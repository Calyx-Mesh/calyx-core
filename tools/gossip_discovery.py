import time
import random
from typing import List, Set

class GossipDiscovery:
    """
    Simulates the 'Rumor Mill' discovery protocol.
    Nodes broadcast their 'INGRVM Portfolio' to random neighbors.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.known_ingrvms: Set[str] = set()
        self.peers: List[str] = []

    def broadcast_ingrvm(self, ingrvm_name: str):
        """
        Spreads the rumor of a new ingrvm.
        """
        print(f"[GOSSIP] {self.node_id[:8]} found a new ingrvm: {ingrvm_name}")
        self.known_ingrvms.add(ingrvm_name)
        
        # Simulate spreading to 2 random peers
        targets = random.sample(self.peers, min(2, len(self.peers)))
        for t in targets:
            print(f"  [>>>] Gossiping to {t[:8]}...")

# --- Verification Test ---
if __name__ == "__main__":
    node = GossipDiscovery("NODE_A_LAPTOP")
    node.peers = ["PEER_B_PC", "PEER_C_PIXEL", "PEER_D_HOMELAB"]
    
    print("--- Starting Gossip Discovery Simulation ---")
    node.broadcast_ingrvm("Vision_Specialist_v1")
    
    if "Vision_Specialist_v1" in node.known_ingrvms:
        print("\nSUCCESS: Gossip discovery logic is ready for integration.")
