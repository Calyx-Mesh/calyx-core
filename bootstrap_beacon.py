import trio
import os
import json
import sys
from libp2p import new_host
from multiaddr import Multiaddr
from libp2p.tools.async_service import background_trio_service

from config import INGRVMConfig
from global_orchestrator import GlobalOrchestrator

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

BEACON_ADDR_FILE = "neuromorphic_env/bootstrap_beacon_addr.txt"

class BootstrapBeacon:
    """
    Phase 7 Task #11: The Auto-Seed Beacon.
    Facilitates mesh discovery by connecting local nodes to 
    global entry points.
    """
    def __init__(self):
        self.conf = INGRVMConfig()
        self.orchestrator = GlobalOrchestrator()
        self.host = None

    async def start(self):
        print_f("--- Starting INGRVM Auto-Seed Beacon (Lighthouse) ---")
        
        # 1. Sync Global Seeds (Task #11 Core)
        print_f("[BEACON] Synchronizing global entry points...")
        self.orchestrator.update_local_bootstrap()
        
        # 2. Identity & Network
        lan_ip = self.conf.get("node", "lan_ip") or "0.0.0.0" 
        p2p_port = 60000 
        
        listen_addr = Multiaddr(f"/ip4/{lan_ip}/tcp/{p2p_port}")
        
        self.host = new_host()
        node_id = self.host.get_id().to_string()
        
        async with self.host.run(listen_addrs=[listen_addr]):
            full_addr = f"/ip4/{lan_ip}/tcp/{p2p_port}/p2p/{node_id}"
            
            # Save address for local discovery fallback
            with open(BEACON_ADDR_FILE, "w") as f:
                f.write(full_addr)
                
            print_f(f"[BEACON] Local ID: {node_id}")
            print_f(f"[BEACON] Public/LAN Address: {full_addr}")
            print_f("[BEACON] Status: ACTIVE. Bridging local mesh to global backbone.")
            
            # 3. Optional: Reach out to other seeds to form a backbone
            # (In a real setup, we would dial peers from bootstrap_list.json here)
            
            await trio.sleep_forever()

async def main():
    beacon = BootstrapBeacon()
    await beacon.start()

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        if os.path.exists(BEACON_ADDR_FILE): os.remove(BEACON_ADDR_FILE)
    except Exception as e:
        print_f(f"[ERROR] Beacon Crash: {e}")

