import trio
import os
import json
import sys
import time
import socket
import datetime
import requests
from typing import Optional, Tuple, List, Dict, Any
from functools import partial
from dotenv import load_dotenv

# --- Resilient Imports ---
try:
    import torch
    import torch.nn as nn
    import snntorch as snn
    HAS_ML = True
except ImportError:
    HAS_ML = False
try:
    from libp2p import new_host
    HAS_P2P = False 
except ImportError:
    HAS_P2P = False

from shard_manager import ShardManager
if HAS_ML:
    from quantization import BinaryLinear
from pipeline_router import PipelineRouter
from pipeline_buffer import PipelineBuffer
from efficiency_monitor import EfficiencyMonitor
from spike_protocol import NeuralSpike, generate_task_id, hash_input, send_spike_raw
from config import INGRVMConfig
from circuit_relay import AutoNAT, INGRVMRelayV2
from hole_puncher import UDP_HolePuncher
from zk_proof_generator import ZKProofGenerator
from brain_models import MiniBrain, MockBrain
from shard_cache import ShardCache

# Import mobile bridge if available
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Mobile'))
    from pytorch_mobile_bridge import INGRVMMobileBridge
    HAS_MOBILE_BRIDGE = True
except ImportError:
    HAS_MOBILE_BRIDGE = False

# Import discovery tool
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
try:
    from lan_discovery import discover_hub
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

class INGRVMNode:
    """
    Core library for a INGRVM Neural Node.
    Handles networking, routing, and brain processing with zk-PoI.
    """
    def __init__(self, node_id: str = "NODE", config_name: str = "shard_config.json", port: int = 60005):
        self.node_id = node_id
        self.config_name = config_name
        self.port = port
        self.conf = INGRVMConfig()
        self.shard_mgr = None
        self.router = None
        self.brain = None
        self.lan_ip = None
        self.eff_monitor = EfficiencyMonitor()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if HAS_ML else None
        self.zk_gen = ZKProofGenerator()
        
        # Load environment variables
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(env_path)

    def log(self, *args):
        text = " ".join(map(str, args))
        print(text, flush=True)
        try:
            log_path = os.getenv("INGRVM_LOG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "node_activity.jsonl"))
            log_entry = {
                "t": datetime.datetime.now().isoformat() + "Z",
                "pid": os.getpid(),
                "event": "NODE_LOG",
                "data": {"text": text}
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
            hub_url = os.getenv("INGRVM_HUB_URL", self.conf.get('node', 'hub_url'))
            hub_log_endpoint = f"{hub_url}/api/mesh/log"
            if os.getenv("INGRVM_NODE_ID") != "PC_MASTER": 
                requests.post(hub_log_endpoint, json={
                    "node_id": os.environ.get("INGRVM_NODE_ID", self.node_id),
                    "event": "REMOTE_LOG",
                    "data": {"text": text},
                    "t": log_entry["t"]
                }, timeout=0.1)
        except Exception: pass

    async def socket_server_loop(self, spike_send_ch):
        async def handler(stream):
            try:
                data = await stream.receive_some(16384)
                if data:
                    spike = NeuralSpike.from_bin(data)
                    
                    # Task #10: Decrypt if necessary
                    if getattr(spike, 'is_encrypted', False):
                        try:
                            spike.decrypt()
                            self.log(f"[SECURE] Decrypted Task: {spike.task_id[:8]}")
                        except Exception as e:
                            self.log(f"[ERROR] [SECURE] Decryption failed: {e}")
                            return

                    self.log(f"[SOCKET] Received Task: {spike.task_id[:8]} | Current Layer: {spike.current_layer}")
                    await spike_send_ch.send(spike)
            except Exception as e:
                self.log(f"[ERROR] Socket error: {e}")

        self.log(f"[SOCKET] Direct Nerve Listening on 0.0.0.0:{self.port}")
        await trio.serve_tcp(handler, self.port, host="0.0.0.0")

    def init_brain(self):
        if self.shard_mgr.local_shards:
            s = self.shard_mgr.local_shards[0]
            self.brain = MiniBrain(s.layer_start, s.layer_end).to(self.device)
            self.log(f"[BRAIN] Shard Loaded: Layers {s.layer_start} to {s.layer_end}")
        else:
            self.brain = MiniBrain(0, 0).to(self.device)

    async def boot(self):
        self.log("!!! NEURAL NODE BOOTING !!!")

        if HAS_ZEROCONF:
            hub_ip, hub_port = discover_hub(timeout=5)
            if hub_ip:
                os.environ["INGRVM_HUB_URL"] = f"http://{hub_ip}:{hub_port}"
                self.log(f"[BOOT] Zeroconf: Connected to Hub at {hub_ip}")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        discovery_path = os.path.join(base_dir, "mesh_discovery")
        
        if "INGRVM" in self.config_name:
            project_root = os.path.dirname(os.path.dirname(base_dir))
            config_path = os.path.abspath(os.path.join(project_root, self.config_name))
        else:
            config_path = os.path.join(base_dir, self.config_name)
        
        self.log(f"DEBUG: Using config_path={config_path}")

        self.shard_mgr = ShardManager("TEMPORARY_ID", discovery_dir=discovery_path, config_path=config_path)
        self.node_id = self.shard_mgr.node_id
        os.environ["INGRVM_NODE_ID"] = self.node_id 
        
        voter = AutoNAT(self.node_id)
        hub_url = os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")
        reachability = await voter.detect_reachability(hub_url)
        
        if reachability == "RESTRICTED":
            self.log("[MESH] Node is behind NAT. Attempting UDP Hole Punch...")
            
            # Task #15: P2P Hardening - Try Hole Punch, fallback to Relay
            # We simulate the target as the PC Hub's public IP
            # (Note: In production, this would be a static bootstrap IP)
            hub_ip_addr = socket.gethostbyname(socket.gethostname()) 
            
            relay = INGRVMRelayV2("PC_MASTER_RELAY")
            puncher = UDP_HolePuncher(self.node_id, relay_manager=relay)
            
            # First, try high-speed relay reservation request
            try:
                resp = requests.post(f"{hub_url}/api/mesh/relay/reserve", json={"node_id": self.node_id}, timeout=5)
                if resp.status_code == 200:
                    path = resp.json().get("relay_path")
                    self.log(f"[BOOT] Relay reservation granted: {path}")
                else:
                    path = await puncher.connect_with_fallback("PC_MASTER", hub_ip_addr, 60001)
            except Exception:
                path = await puncher.connect_with_fallback("PC_MASTER", hub_ip_addr, 60001)
            
            if "p2p-circuit" in path:
                self.log(f"[BOOT] Hole Punch FAILED. Fallback Relay Active: {path}")
            else:
                self.log(f"[BOOT] Hole Punch SUCCESS. Direct Path: {path}")
                
            self.shard_mgr.relay_addrs[self.node_id] = path

        self.lan_ip = os.getenv("INGRVM_NODE_IP", socket.gethostbyname(socket.gethostname()))
        self.log(f"--- INGRVM Neural Node: {self.node_id} ---")
        self.log(f"IP: {self.lan_ip}")

        self.init_brain()
        self.router = PipelineRouter(self.shard_mgr)

    async def run(self):
        await self.boot()
        async with trio.open_nursery() as nursery:
            spike_send_ch, spike_recv_ch = trio.open_memory_channel(10)
            self.shard_mgr.file_spike_queue = spike_send_ch

            nursery.start_soon(self.socket_server_loop, spike_send_ch)
            nursery.start_soon(self.shard_mgr.broadcast_shards, None) 
            nursery.start_soon(self.shard_mgr.poll_mesh_files)  

            async for spike in spike_recv_ch:
                await self.process_spike(spike, spike_send_ch)

    async def process_spike(self, spike: NeuralSpike, spike_send_ch):
        try:
            current_layer = getattr(spike, 'current_layer', 0)
            self.log(f"[SPIKE] Processing Task: {spike.task_id[:8]} | Layer {current_layer}")
            
            if spike.hop_count >= spike.ttl:
                self.log(f"[WARN] TTL Expired for {spike.task_id[:8]}")
                return

            if not (self.brain.layer_start <= current_layer <= self.brain.layer_end):
                self.log(f"[ROUTING] Node {self.node_id} does not own Layer {current_layer}. Rerouting...")
                target_node = self.shard_mgr.find_next_hop(getattr(spike, 'model_name', 'INGRVM-1.0'), current_layer, look_for_current=True)
                if target_node and target_node != "LOCAL":
                    # Task #10: Encrypt outgoing reroute
                    spike.encrypt()
                    peer_ip = self.shard_mgr.get_peer_ip(target_node)
                    if peer_ip:
                        await send_spike_raw(spike, peer_ip, self.port)
                    else:
                        self.shard_mgr.send_file_spike(target_node, spike.to_bin())
                return

            # Process through local layers
            if HAS_ML:
                input_tensor = torch.tensor(spike.get_spikes()).float().to(self.device)
                output_tensor, next_layer_idx, execution_steps = self.brain(input_tensor, current_layer)
                spike.set_spikes(output_tensor.view(-1).tolist())
            else:
                next_layer_idx, execution_steps = self.brain(None, current_layer)[1:]
            
            # --- zkML: Generate Proof of Inference ---
            self.log(f"[zkML] Generating Proof for Layer {current_layer}...")
            poi = self.zk_gen.generate_poi(
                model_id=getattr(spike, 'model_name', 'INGRVM-1.0'),
                input_hash=spike.input_hash,
                output_data=spike.get_spikes(),
                execution_steps=execution_steps
            )
            spike.poi_packet = poi
            
            # Update Spike state
            spike.hop_count += 1
            spike.current_layer = next_layer_idx
            
            dest, target_peer = self.router.route_spike(spike)
            if dest == "LOCAL":
                await spike_send_ch.send(spike)
            elif dest == "PEER":
                self.log(f"[ROUTING] Forwarding to {target_peer} for Layer {spike.current_layer}")
                
                # Task #10: Encrypt outgoing spike
                spike.encrypt()
                
                peer_ip = self.shard_mgr.get_peer_ip(target_peer)
                success = False
                if peer_ip:
                    success = await send_spike_raw(spike, peer_ip, self.port)
                if not success:
                    await self.shard_mgr.send_file_spike(target_peer, spike.to_bin())
            else:
                self.log(f"[FINISH] Sequence Complete: {spike.task_id[:8]}")
        except Exception as e:
            self.log(f"[ERROR] Error in processing loop: {e}")
            import traceback
            traceback.print_exc()

class INGRVMMobileNode(INGRVMNode):
    """
    Mobile-optimized variant of the INGRVM Node.
    Uses INGRVMMobileBridge for .ingrvm loading and NPU optimization.
    Supports Task #10: Persistent Shard Caching.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bridge = INGRVMMobileBridge() if HAS_MOBILE_BRIDGE else None
        self.cache = ShardCache()

    def init_brain(self):
        if not self.bridge:
            super().init_brain()
            return

        if not self.shard_mgr.local_shards:
            super().init_brain()
            return
            
        shard = self.shard_mgr.local_shards[0]
        model_name = shard.model_name
        
        self.log(f"[MOBILE] Initializing Optimized Brain for {model_name}...")

        # 1. Check Persistent Cache (Task #10)
        cached_weights = self.cache.load_shard(model_name, shard.layer_start, shard.layer_end)
        
        if cached_weights:
            self.log("[CACHE] Instant Restart: Loading weights from local Vector DB.")
            # Instantiate base architecture
            super().init_brain()
            # Apply optimizations directly
            self.brain = self.bridge.load_optimized_shard(self.brain, cached_weights)
            self.log("✅ [CACHE] Shard Restored & Optimized.")
            return

        # 2. If not in cache, locate local .ingrvm file
        mobile_ingrvms_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Mobile', 'ingrvms')
        
        # Look for a file like 'sentiment_alpha_1.0.2.ingrvm'
        package_path = None
        if os.path.exists(mobile_ingrvms_dir):
            for f in os.listdir(mobile_ingrvms_dir):
                if f.startswith(model_name) and f.endswith(".ingrvm"):
                    package_path = os.path.join(mobile_ingrvms_dir, f)
                    break
        
        if not package_path:
            self.log(f"[WARN] No .ingrvm package found for {model_name}. Falling back to Mock.")
            super().init_brain()
            return

        # 3. Unpack, Load, and Cache
        self.log(f"[MOBILE] Loading Shard from {os.path.basename(package_path)}...")
        try:
            package_data = self.bridge.unpack_ingrvm(package_path)
            
            # Instantiate base architecture
            super().init_brain() 
            
            # Apply optimizations
            self.brain = self.bridge.load_optimized_shard(self.brain, package_data["weights"])
            
            # Save to Cache for next time (Task #10)
            self.cache.save_shard(model_name, shard.layer_start, shard.layer_end, package_data["weights"])
            
            self.log(f"✅ [MOBILE] Shard Optimized Loaded & Cached.")
        except Exception as e:
            self.log(f"[ERROR] [MOBILE] Failed to load optimized shard: {e}")
            super().init_brain()
