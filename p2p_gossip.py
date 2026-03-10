import trio
import json
import time
import os
import sys
from typing import Dict, List, Optional, Callable
from pathlib import Path

# libp2p imports
try:
    from libp2p import new_host
    from libp2p.pubsub import floodsub, gossipsub
    from libp2p.pubsub.pubsub import Pubsub
    from multiaddr import Multiaddr
    HAS_P2P = True
except ImportError:
    HAS_P2P = False

class INGRVMGossipNode:
    """
    Phase 9 Task #4: Gossip V1 implementation.
    Uses libp2p PubSub for decentralized block propagation and mesh state.
    """
    def __init__(self, node_id: str, port: int = 60001):
        self.node_id = node_id
        self.port = port
        self.host = None
        self.pubsub = None
        self.topics: Dict[str, Any] = {}
        self.callbacks: Dict[str, List[Callable]] = {
            "blocks": [],
            "state": []
        }

    async def start(self):
        if not HAS_P2P:
            print("⚠️ [GOSSIP] libp2p not fully available. Running in MOCK mode.")
            return

        # 1. Initialize libp2p Host
        self.host = new_host()
        async with self.host.run():
            listen_addr = f"/ip4/0.0.0.0/tcp/{self.port}"
            print(f"[GOSSIP] Node {self.node_id[:8]} listening on {listen_addr}")
            
            # 2. Initialize PubSub (Gossipsub preferred)
            # Note: Gossipsub is more efficient for larger meshes
            router = gossipsub.GossipsubRouter()
            self.pubsub = Pubsub(self.host, router)
            
            # 3. Subscribe to core topics
            await self.subscribe("INGRVM_BLOCKS", self._on_block)
            await self.subscribe("INGRVM_STATE", self._on_state)
            
            print(f"[GOSSIP] Subscribed to core mesh topics.")
            
            # Keep alive
            while True:
                await trio.sleep(3600)

    async def subscribe(self, topic_name: str, callback: Callable):
        """ Subscribes to a topic and registers a handler. """
        if not self.pubsub: return
        
        if topic_name not in self.topics:
            self.topics[topic_name] = await self.pubsub.subscribe(topic_name)
            
        # Register the callback logic
        async def listener():
            async for msg in self.topics[topic_name]:
                await callback(msg)
        
        # In a real trio app, we'd spawn this in a nursery
        return listener

    async def broadcast(self, topic_name: str, data: Dict):
        """ Broadcasts a message to the mesh. """
        msg_bin = json.dumps(data).encode('utf-8')
        if self.pubsub:
            await self.pubsub.publish(topic_name, msg_bin)
            print(f"📡 [GOSSIP] Broadcasted to {topic_name}: {list(data.keys())}")
        else:
            print(f"📡 [MOCK-GOSSIP] Broadcasted to {topic_name}: {list(data.keys())}")

    # --- Handlers ---

    async def _on_block(self, msg):
        data = json.loads(msg.data.decode('utf-8'))
        print(f"📦 [GOSSIP] Received NEW BLOCK: {data.get('block_hash', '???')[:16]}...")
        for cb in self.callbacks["blocks"]:
            await cb(data)

    async def _on_state(self, msg):
        data = json.loads(msg.data.decode('utf-8'))
        print(f"📈 [GOSSIP] Received state update from {data.get('node_id', 'UNK')[:8]}")
        for cb in self.callbacks["state"]:
            await cb(data)

    def register_callback(self, category: str, cb: Callable):
        if category in self.callbacks:
            self.callbacks[category].append(cb)

# --- Module Test ---
if __name__ == "__main__":
    async def test_gossip():
        node = INGRVMGossipNode("LAPTOP_RELAY_TEST")
        
        # Test broadcast (even in mock mode)
        mock_block = {
            "block_id": 99,
            "block_hash": "0xABC123DEADBEEF",
            "merkle_root": "0xROOT",
            "timestamp": time.time()
        }
        
        await node.broadcast("INGRVM_BLOCKS", mock_block)
        print("✅ Gossip logic initialized.")

    trio.run(test_gossip)
