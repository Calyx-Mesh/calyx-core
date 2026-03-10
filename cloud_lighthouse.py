import trio
import os
import json
import socket
import sys
import time
from typing import List, Dict, Optional
from libp2p import new_host
from multiaddr import Multiaddr

from config import INGRVMConfig
from global_orchestrator import GlobalOrchestrator
from ipfs_storage import CIDStorage

class CloudLighthouse:
    """
    Phase 8: The Global Neural Anchor.
    A publicly reachable node that facilitates anonymous P2P hole-punching,
    provides WAN relaying, and serves as a global skill cache.
    """
    def __init__(self, port: int = 60000, api_port: int = 8080):
        self.port = port
        self.api_port = api_port
        self.orchestrator = GlobalOrchestrator()
        self.storage = CIDStorage(root_dir="neuromorphic_env/lighthouse_cache")
        self.peer_id = None
        self.public_addr = None

    async def run(self):
        print(f"--- [PHASE 8] INGRVM CLOUD LIGHTHOUSE INITIALIZING ---")
        
        # 1. Sync Neural Backbone
        print("[LIGHTHOUSE] Syncing with global bootstrap list...")
        self.orchestrator.update_local_bootstrap()

        # 2. Network Identity (Anonymous Ed25519)
        # We bind to 0.0.0.0 because this is meant for public cloud deployment
        self.host = new_host()
        self.peer_id = self.host.get_id().to_string()
        
        listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.port}")
        
        async with self.host.run(listen_addrs=[listen_addr]):
            # 3. Detect Public IP (Simulated/Auto)
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            self.public_addr = f"/ip4/{local_ip}/tcp/{self.port}/p2p/{self.peer_id}"
            
            print(f"[LIGHTHOUSE] Node ID: {self.peer_id}")
            print(f"[LIGHTHOUSE] Binding Address: {self.public_addr}")
            print(f"[LIGHTHOUSE] Status: ONLINE. Awaiting mesh connections.")

            # 4. Multi-Hub Relay Logic (Mock)
            # In Phase 8, the lighthouse keeps connections open to forward 
            # spikes across different LANs.
            await self._backbone_relay_loop()

    async def _backbone_relay_loop(self):
        """ Keeps the lighthouse active as a persistent relay. """
        print("[LIGHTHOUSE] Relay V2 active. Anonymous hole-punching enabled.")
        while True:
            # Periodically announce self to global registry (Mock)
            self.orchestrator.announce_self(self.public_addr, self.peer_id)
            await trio.sleep(300) # Every 5 mins

if __name__ == "__main__":
    lighthouse = CloudLighthouse()
    try:
        trio.run(lighthouse.run)
    except KeyboardInterrupt:
        print("\n[LIGHTHOUSE] Shutting down neural anchor.")
    except Exception as e:
        print(f"❌ [LIGHTHOUSE ERROR] {e}")

