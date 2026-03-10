import trio
import json
import time
import os
import requests
from typing import Dict, List, Optional
try:
    from multiaddr import Multiaddr
    HAS_MULTIADDR = True
except ImportError:
    HAS_MULTIADDR = False
    class Multiaddr:
        def __init__(self, addr): self.addr = addr
        def __str__(self): return str(self.addr)

class INGRVMRelayV2:
    """
    Phase 7 Task #4: libp2p Relay v2 implementation (Functional Mock).
    Acts as a bridge for nodes behind symmetric NATs or restrictive firewalls.
    """
    def __init__(self, relay_id: str, port: int = 60000):
        self.relay_id = relay_id
        self.port = port
        self.public_ip = self._get_public_ip()
        self.reservations: Dict[str, float] = {} # NodeID -> Expiry
        
        print(f"[RELAY-V2] Relay initialized at /ip4/{self.public_ip}/tcp/{port}/p2p/{relay_id}")

    def _get_public_ip(self):
        try:
            return requests.get("https://api.ipify.org", timeout=5).text
        except:
            return "127.0.0.1"

    def request_reservation(self, node_id: str, duration: int = 3600) -> Optional[str]:
        """
        Simulates the Relay v2 reservation protocol.
        """
        print(f"[RELAY-V2] Processing reservation for {node_id[:8]}...")
        expiry = time.time() + duration
        self.reservations[node_id] = expiry
        
        # Format: /ip4/<relay_ip>/tcp/<relay_port>/p2p/<relay_id>/p2p-circuit/p2p/<node_id>
        relay_path = f"/ip4/{self.public_ip}/tcp/{self.port}/p2p/{self.relay_id}/p2p-circuit/p2p/{node_id}"
        return relay_path

    async def run_cleanup_loop(self):
        while True:
            now = time.time()
            self.reservations = {k: v for k, v in self.reservations.items() if v > now}
            await trio.sleep(60)

class AutoNAT:
    """
    Phase 7 Task #5: Reachability detection.
    Helps a node decide if it needs to request a Relay reservation.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id

    async def detect_reachability(self, hub_url: str) -> str:
        """
        Detects if the node is reachable from the outside world.
        """
        print(f"[AUTONAT] Probing reachability for {self.node_id[:8]}...")
        
        # In a real setup, we'd use a STUN server or Hub-back-dial.
        # Here we check if we are on a private IP range.
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
        
        if local_ip.startswith("192.168.") or local_ip.startswith("10."):
            print(f"[AUTONAT] Node is on Private IP ({local_ip}). Status: RESTRICTED.")
            return "RESTRICTED"
        
        print(f"[AUTONAT] Node appears to have Public IP ({local_ip}). Status: DIRECT.")
        return "PUBLIC"

if __name__ == "__main__":
    async def test_relay_flow():
        # 1. Setup
        relay = INGRVMRelayV2("12D3KooW_MASTER_RELAY")
        voter = AutoNAT("LAPTOP_RELAY")
        
        # 2. Check
        status = await voter.detect_reachability("http://pc-master:8000")
        
        if status == "RESTRICTED":
            # 3. Request Relay Reservation
            public_path = relay.request_reservation("LAPTOP_RELAY")
            print(f"\n✅ SUCCESS: WAN-Ready Multiaddr generated.")
            print(f"Path: {public_path}")

    trio.run(test_relay_flow)

