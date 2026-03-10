import trio
import json
from typing import Optional, Tuple
from spike_protocol import NeuralSpike, send_spike_raw
from shard_manager import ShardManager

class PipelineRouter:
    """
    The Pipeline Router decides WHERE a spike goes next.
    It links the SNN inference logic with the P2P networking.
    """
    def __init__(self, shard_mgr: ShardManager):
        self.shard_mgr = shard_mgr

    def route_spike(self, spike: NeuralSpike) -> Tuple[str, Optional[str]]:
        """
        Determines the next destination for a spike.
        Returns: (destination_type, target_node_id)
        destination_type: "LOCAL", "PEER", or "END" (if model finished)
        """
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        model_name = get_attr(spike, "model_name", "INGRVM-1.0")
        current_layer = get_attr(spike, "current_layer", 0)

        # 1. Is this node responsible for the NEXT layer?
        next_hop = self.shard_mgr.find_next_hop(model_name, current_layer)
        
        if next_hop == "LOCAL":
            return "LOCAL", None
        elif next_hop:
            return "PEER", next_hop
        else:
            # Task Complete -> Route back to Hub
            return "END", "PC_MASTER"

    async def forward_spike(self, pubsub, topic: str, spike: NeuralSpike, target_node_id: str):
        """
        Actually sends the spike to the mesh.
        """
        # Task #04: Mesh Safety (TTL & Hop Count)
        if spike.hop_count >= spike.ttl:
            print(f"[MESH-SAFETY] DROPPING Spike {spike.task_id} (TTL EXPIRED)")
            return

        target_ip = None
        
        # 1. Resolve Target IP
        if target_node_id == "PC_MASTER":
            target_ip = "192.168.68.51" # Hardcoded Hub IP for resilience
        elif target_node_id in self.shard_mgr.mesh_shards:
            target_ip = self.shard_mgr.mesh_shards[target_node_id][0].node_ip
            
        print(f"[ROUTER] Forwarding Task {spike.task_id[:8]} to {target_node_id} (Hop: {spike.hop_count})")
        
        # 2. Try Direct LAN Socket (Fastest)
        if target_ip and target_ip != "127.0.0.1":
            if await send_spike_raw(spike, target_ip):
                print(f"[ROUTER] Dispatched via Direct Socket to {target_ip}")
                return

        # 3. Try P2P PubSub
        if pubsub:
            await pubsub.publish(topic, spike.to_bin())
            print(f"[ROUTER] Dispatched via P2P PubSub to {target_node_id}")
            return

        # 4. Last Resort: File-based Postal Service (Task #07)
        print(f"[ROUTER] Socket/P2P Failed. Falling back to Postal Service for {target_node_id}")
        self.shard_mgr.send_file_spike(target_node_id, spike.to_bin())

# --- Simple Verification ---
async def test_router():
    mgr = ShardManager("NODE_A")
    mgr.register_shard("INGRVM-1.0", 0, 5, 1.0)
    
    router = PipelineRouter(mgr)
    
    spike = NeuralSpike(
        task_id="TEST_TASK",
        ingrvm_id="ingrvm_0",
        node_id="NODE_A",
        input_hash="hash",
        current_layer=4, # We just finished layer 4
        model_name="INGRVM-1.0"
    )
    
    dest, peer = router.route_spike(spike)
    print(f"Route for Layer 5: {dest} (Target: {peer})")
    
    # Mock finding a peer for layer 6
    mgr.mesh_shards["PEER_B"] = [
        # Use the actual dataclass for consistent test behavior
        ModelShard(model_name="INGRVM-1.0", layer_start=6, layer_end=10, node_id="PEER_B")
    ]
    
    spike.current_layer = 5 # Finished layer 5
    dest, peer = router.route_spike(spike)
    print(f"Route for Layer 6: {dest} (Target: {peer})")

if __name__ == "__main__":
    trio.run(test_router)
