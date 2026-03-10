import trio
import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

# --- Shard Metadata ---
@dataclass
class ModelShard:
    model_name: str
    layer_start: int
    layer_end: int
    node_id: str
    node_ip: str = "127.0.0.1" # Added for raw socket fallback
    vram_usage_gb: float = 0.0
    is_ready: bool = True

from config import INGRVMConfig

conf = INGRVMConfig()

class ShardManager:
    """
    Handles Model Sharding across the mesh.
    Supports both P2P (FloodSub) and File-based discovery for resilience.
    """
    def __init__(self, node_id: str, discovery_dir: Optional[str] = None, config_path: Optional[str] = None):
        self.node_id = node_id
        # Use config or defaults for discovery directory
        self.discovery_dir = discovery_dir or os.getenv("INGRVM_DISCOVERY_DIR", "mesh_discovery")
        config_path = config_path or os.getenv("INGRVM_SHARD_CONFIG", "shard_config.json")
        
        self.local_shards: List[ModelShard] = []
        self.mesh_shards: Dict[str, List[ModelShard]] = {} # node_id -> shards
        self.relay_addrs: Dict[str, str] = {} # node_id -> relay_multiaddr (Task #04)
        self.file_spike_queue = None # Set by neural_node
        
        if not os.path.exists(self.discovery_dir):
            os.makedirs(self.discovery_dir)

        # Task #02: Load from Node-Specific Shard Config
        if os.path.exists(config_path):
            self.load_config(config_path)

    def load_config(self, path: str):
        """ Loads shard definitions from a JSON file. """
        try:
            with open(path, "r") as f:
                config = json.load(f)
                if "node_name" in config:
                    self.node_id = config["node_name"]
                    print(f"[SHARD] Node ID updated from config: {self.node_id}")
                ip = config.get("lan_ip", "127.0.0.1")
                for s in config.get("shards", []):
                    self.register_shard(
                        model_name=s.get("model_name", "INGRVM-1.0"),
                        start=s.get("layer_start", 0),
                        end=s.get("layer_end", 0),
                        vram_gb=s.get("vram_usage_gb", 0.0),
                        ip=ip
                    )
                print(f"[SHARD] Loaded {len(self.local_shards)} shards from {path}")
        except Exception as e:
            print(f"[ERROR] Failed to load shard config: {e}")

    def register_shard(self, model_name: str, start: int, end: int, vram_gb: float, ip: str = "127.0.0.1"):
        shard = ModelShard(
            model_name=model_name,
            layer_start=start,
            layer_end=end,
            node_id=self.node_id,
            node_ip=ip,
            vram_usage_gb=vram_gb
        )
        self.local_shards.append(shard)
        print(f"[SHARD] Registered local shard: {model_name} (Layers {start}-{end})")
        self._write_local_discovery_file()
        return shard

    def _write_local_discovery_file(self):
        """ Write shard info to a local file for non-P2P discovery. """
        path = os.path.join(self.discovery_dir, f"{self.node_id}.json")
        timestamp = time.time()
        data = {
            "node_id": self.node_id,
            "shards": [asdict(s) for s in self.local_shards],
            "last_seen": timestamp
        }
        with open(path, "w") as f:
            json.dump(data, f)

    async def _resilient_sleep(self, seconds: float):
        """ Helper to sleep using the active event loop. """
        try:
            await trio.sleep(seconds)
        except Exception:
            await asyncio.sleep(seconds)

    async def poll_mesh_files(self):
        """ Periodically check for shard files AND incoming file-based spikes. """
        while True:
            try:
                await trio.to_thread.run_sync(self._sync_poll_logic)
            except Exception:
                await asyncio.to_thread(self._sync_poll_logic)
            await self._resilient_sleep(1)

    def _sync_poll_logic(self):
        """ Blocking file logic moved to a thread. """
        current_time = time.time()
        discovered_nodes = []
        if os.path.exists(self.discovery_dir):
            for filename in os.listdir(self.discovery_dir):
                if filename.endswith(".json") and not filename.startswith(self.node_id):
                    try:
                        path = os.path.join(self.discovery_dir, filename)
                        with open(path, "r") as f:
                            data = json.load(f)
                            last_seen = data.get("last_seen", 0)
                            if current_time - last_seen > 3600:
                                continue
                            sender_id = data["node_id"]
                            shards = []
                            for s in data["shards"]:
                                if isinstance(s, dict):
                                    shards.append(ModelShard(**s))
                                else:
                                    shards.append(s)
                            self.mesh_shards[sender_id] = shards
                            discovered_nodes.append(sender_id)
                    except Exception: pass
        
        for node_id in list(self.mesh_shards.keys()):
            if node_id not in discovered_nodes:
                del self.mesh_shards[node_id]

        # 2. File-based Spike Relay
        spike_dir = os.path.join(self.discovery_dir, "spikes_in")
        if os.path.exists(spike_dir):
            files = os.listdir(spike_dir)
            for spike_file in files:
                if spike_file.startswith(f"to_{self.node_id}"):
                    path = os.path.join(spike_dir, spike_file)
                    try:
                        with open(path, "rb") as f:
                            spike_bin = f.read()
                        if self.file_spike_queue:
                            from spike_protocol import NeuralSpike
                            spike = NeuralSpike.from_bin(spike_bin)
                            trio.from_thread.run_sync(self.file_spike_queue.send_nowait, spike)
                        os.remove(path)
                    except Exception: pass

    def send_file_spike(self, target_node_id: str, spike_bin: bytes):
        """ Writes a spike to the shared folder for the target node to find. """
        spike_dir = os.path.join(self.discovery_dir, "spikes_in")
        if not os.path.exists(spike_dir): os.makedirs(spike_dir)
        filename = f"to_{target_node_id}_{int(time.time())}.bin"
        final_path = os.path.join(spike_dir, filename)
        tmp_path = final_path + ".tmp"
        try:
            with open(tmp_path, "wb") as f:
                f.write(spike_bin)
            os.replace(tmp_path, final_path)
        except Exception:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    async def broadcast_shards(self, pubsub=None, topic: str = "ingrvm/mesh/discovery"):
        while True:
            self._write_local_discovery_file()
            if pubsub:
                payload = {
                    "type": "SHARD_ANNOUNCEMENT",
                    "node_id": self.node_id,
                    "shards": [asdict(s) for s in self.local_shards]
                }
                try:
                    await pubsub.publish(topic, json.dumps(payload).encode('utf-8'))
                except Exception: pass
            await self._resilient_sleep(5)

    def get_peer_ip(self, node_id: str) -> Optional[str]:
        if node_id in self.mesh_shards and self.mesh_shards[node_id]:
            return self.mesh_shards[node_id][0].node_ip
        return None

    def get_peer_multiaddr(self, node_id: str) -> Optional[str]:
        ip = self.get_peer_ip(node_id)
        if not ip: return None
        if node_id in self.relay_addrs:
            return self.relay_addrs[node_id]
        return f"/ip4/{ip}/tcp/60001"

    def find_next_hop(self, model_name: str, current_layer: int, look_for_current: bool = False) -> Optional[str]:
        target_layer = current_layer if look_for_current else current_layer + 1
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict): return obj.get(key, default)
            return getattr(obj, key, default)
        for shard in self.local_shards:
            if get_attr(shard, "is_ready") and get_attr(shard, "model_name") == model_name and \
               get_attr(shard, "layer_start", 0) <= target_layer <= get_attr(shard, "layer_end", 0):
                return "LOCAL"
        for node_id, shards in self.mesh_shards.items():
            for shard in shards:
                if get_attr(shard, "is_ready") and get_attr(shard, "model_name") == model_name and \
                   get_attr(shard, "layer_start", 0) <= target_layer <= get_attr(shard, "layer_end", 0):
                    return node_id
        return None

if __name__ == "__main__":
    async def test():
        mgr = ShardManager("TEST_NODE")
        mgr.register_shard("TestModel", 0, 10, 1.0)
        print("Shard file written to mesh_discovery/")
    trio.run(test)
