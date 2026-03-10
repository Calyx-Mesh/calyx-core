import requests
import json
import os
import time
from typing import List, Dict, Any, Optional

class GlobalOrchestrator:
    """
    Phase 8: The Global Orchestrator.
    Connects local hubs into a global neural fabric by 
    synchronizing bootstrap nodes from a central registry.
    """
    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url or "https://raw.githubusercontent.com/INGRVM-Mesh/Network/master/bootstrap_nodes.json"
        
        # Resolve path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.local_bootstrap_path = os.path.join(base_dir, "bootstrap_list.json")

    def fetch_global_peers(self) -> List[str]:
        """ Fetches the latest master bootstrap list from the global registry. """
        print(f"[GLOBAL] Syncing with neural backbone: {self.registry_url}")
        try:
            resp = requests.get(self.registry_url, timeout=5)
            if resp.status_code == 200:
                peers = resp.json().get("nodes", [])
                print(f"[GLOBAL] Found {len(peers)} global entry points.")
                return peers
        except Exception as e:
            print(f"[ERROR] Global sync failed: {e}")
        return []

    def update_local_bootstrap(self):
        """ Merges global peers into the local bootstrap list. """
        global_peers = self.fetch_global_peers()
        if not global_peers:
            return

        # Load existing
        local_peers = []
        if os.path.exists(self.local_bootstrap_path):
            with open(self.local_bootstrap_path, "r") as f:
                local_peers = json.load(f)

        # Merge and Deduplicate
        updated_list = list(set(local_peers + global_peers))
        
        with open(self.local_bootstrap_path, "w") as f:
            json.dump(updated_list, f, indent=4)
            
        print(f"[GLOBAL] Local bootstrap updated. Total nodes known: {len(updated_list)}")

    def announce_self(self, hub_ip: str, node_id: str):
        """ 
        (Mock) Announces this Hub to the global registry.
        In a production environment, this would be a signed POST request.
        """
        print(f"[GLOBAL] Announcing {node_id} at {hub_ip} to the backbone...")
        # Simulated success
        time.sleep(1)
        print("[GLOBAL] Announcement broadcasted.")

if __name__ == "__main__":
    orch = GlobalOrchestrator()
    orch.update_local_bootstrap()

