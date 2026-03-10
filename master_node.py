import trio
import os
import sys
import torch
from libp2p import new_host
from libp2p.pubsub.pubsub import Pubsub
from libp2p.pubsub.floodsub import FloodSub
from multiaddr import Multiaddr
from functools import partial

# --- INGRVM Module Imports ---
from config import INGRVMConfig
from identity_manager import NodeIdentity
from metabolism import NodeMetabolism
from spike_protocol import NeuralSpike
from spike_sanitizer import SpikeSanitizer
from spike_queue import PrioritizedSpikeQueue
from reward_validator import RewardValidator
from thalamus import ThalamusRouter
from mercenary_log import MercenaryLogger
from peer_database import PeerDatabase
from shard_manager import ShardManager

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)
class INGRVMMasterNode:
    """
    The Completed Cortex.
    Wires all 17+ logical modules into a watertight neural pipeline.
    """
    def __init__(self):
        self.is_active = True # Circuit Breaker Flag
        self.conf = INGRVMConfig()
        # ... (rest of init)

        self.identity = NodeIdentity()
        self.node_id = self.identity.get_public_key_b64()
        
        # Security & Validation
        self.sanitizer = SpikeSanitizer()
        self.validator = RewardValidator()
        self.db = PeerDatabase(db_path="peer_db.json")
        
        # Vitality & Resources
        self.metabolism = NodeMetabolism(
            max_energy=self.conf.get("economy", "max_energy_joules"),
            recovery_rate=self.conf.get("economy", "solar_recovery_rate")
        )
        
        # Intelligence & Routing
        self.router = ThalamusRouter()
        self.queue = PrioritizedSpikeQueue(max_size=self.conf.get("security", "max_queue_size"))
        self.logger = MercenaryLogger(self.node_id)
        
        # Discovery
        self.shard_mgr = ShardManager(self.node_id)

    async def cortex_pipeline(self, spike_bin: bytes, peer_id: str):
        """
        The Watertight Assembly Line for incoming spikes.
        """
        if not self.is_active:
            print_f("[CRITICAL] Circuit Breaker Active. Dropping spike.")
            return

        # Metabolic Sleep Check
        if self.metabolism.current_energy < 50:
            print_f("[VITALITY] Critical Energy Low. Entering Metabolic Sleep.")
            return

        # 1. DECODE (Binary Unpack)
        try:
            spike = NeuralSpike.from_bin(spike_bin)
        except Exception:
            self.logger.log_event("DECODE_ERROR", {"peer": peer_id})
            return

        # 2. VALIDATE (Signature Check)
        ok, status = self.validator.verify_spike_integrity(spike)
        if not ok:
            self.logger.log_event("AUTH_DENIED", {"reason": status, "peer": peer_id})
            return

        # 3. SANITIZE (Neutralize Toxic Spikes)
        spike.sparse_indices = self.sanitizer.sanitize(spike.sparse_indices)

        # 4. METABOLISM (Energy Check)
        if not self.metabolism.consume_spikes(len(spike.sparse_indices)):
            self.logger.log_event("RESOURCE_LOW", {"energy": self.metabolism.current_energy})
            return

        # 5. QUEUE (Reputation-based Priority)
        peer_record = self.db.get_peer(spike.node_id)
        reputation = peer_record.reputation if peer_record else 1.0
        self.queue.push(reputation, spike.task_id, spike.sparse_indices)

        # 6. PROCESS (Thalamus Routing to SNN Brain)
        print_f(f"[CORTEX] Task {spike.task_id} authorized and queued.")
        result = await self.router.route_spike(spike)
        
        if result:
            self.logger.log_event("SUCCESS", {"task": spike.task_id})

    async def run(self):
        # Setup libp2p
        port = self.conf.get('node', 'p2p_port')
        listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        host = new_host()
        
        pubsub_impl = FloodSub(protocols=['/floodsub/1.0.0'])
        pubsub = Pubsub(host, pubsub_impl)
        
        async with host.run(listen_addrs=[listen_addr]), trio.open_nursery() as nursery:
            print_f(f"\n--- [INGRVM MASTER NODE ONLINE] ---")
            print_f(f"ID: {self.node_id}")
            
            # Start Background Vitals
            nursery.start_soon(self.shard_mgr.poll_mesh_files)
            
            # Simulated Listen Loop (Bridges P2P/File/Socket to Cortex)
            # In a real run, this would be the actual subscription loop
            await trio.sleep_forever()

if __name__ == "__main__":
    node = INGRVMMasterNode()
    try:
        trio.run(node.run)
    except KeyboardInterrupt:
        print_f("\n[HIBERNATE] Cortex powered down.")

