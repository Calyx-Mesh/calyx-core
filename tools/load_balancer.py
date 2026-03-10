import random
from typing import List, Dict

class MetabolicLoadBalancer:
    """
    Intelligent Router for the INGRVM Mesh.
    Chooses the 'healthiest' peer for a neural hop based on 
    Reputation and Metabolic Energy (Mocked).
    """
    def __init__(self):
        print("[ROUTER] Metabolic Load Balancer initialized.")

    def select_next_hop(self, peers: List[Dict]) -> Dict:
        """
        Input: List of peer records with energy and reputation.
        Logic: Sort by a 'Vitality Score' (Reputation * Energy).
        """
        scored_peers = []
        for p in peers:
            # Vitality = Reputation (0-2) * Energy (0-100)
            vitality = p['reputation'] * p.get('energy', 50)
            scored_peers.append({**p, "vitality": vitality})
        
        # Sort by vitality descending
        scored_peers.sort(key=lambda x: x['vitality'], reverse=True)
        
        # Return the winner (top 1) or random from top 3 for decentralization
        winner = scored_peers[0]
        print(f"[ROUTER] Route chosen: {winner['peer_id'][:8]} (Vitality: {winner['vitality']:.1f})")
        return winner

# --- Verification Test ---
if __name__ == "__main__":
    balancer = MetabolicLoadBalancer()
    
    # Mock data from 3 potential neighbors
    candidates = [
        {"peer_id": "12D3_TIER_1_PC", "reputation": 1.9, "energy": 95},
        {"peer_id": "12D3_PIXEL_8", "reputation": 1.5, "energy": 20}, # Low battery!
        {"peer_id": "12D3_OLD_LAPTOP", "reputation": 0.8, "energy": 80}
    ]
    
    best = balancer.select_next_hop(candidates)
    
    if best['peer_id'] == "12D3_TIER_1_PC":
        print("\nSUCCESS: Load balancer correctly prioritized high-energy, high-trust node.")
    else:
        print("\nFAILURE: Suboptimal node chosen.")

