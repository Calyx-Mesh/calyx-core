import torch
import torch.nn as nn
import snntorch as snn
from collections import defaultdict
from typing import List, Dict, Tuple
from peer_database import PeerDatabase

class WeightedEnsemble:
    """
    Prevents Sybil Attacks by weighting decisions based on $DOPA stake and Reputation.
    Integrates directly with the persistent PeerDatabase.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db

    def get_consensus(self, node_outputs: Dict[str, List[int]]) -> Tuple[List[int], float]:
        """
        node_outputs: Map of PeerID -> Binary Spike List
        Returns: (Consensus Decision, Confidence Score)
        """
        print(f"\n--- [SECURITY] Commencing Weighted Consensus (Nodes: {len(node_outputs)}) ---")
        
        # 1. Accumulate weighted votes for each unique output pattern
        # Decision (tuple) -> Total Weight (float)
        weighted_votes = defaultdict(float)
        total_mesh_weight = 0.0
        
        for peer_id, output in node_outputs.items():
            record = self.db.get_peer(peer_id)
            
            # Weight = (Tokens Earned/Staked * Reputation)
            # Starting nodes have a baseline weight of 1.0
            if record:
                weight = (1.0 + record.tokens_earned) * record.reputation
            else:
                weight = 1.0 # Unknown nodes get minimum weight
                
            pattern = tuple(output)
            weighted_votes[pattern] += weight
            total_mesh_weight += weight
            
            print(f"  > Node {peer_id[:8]}... | Weight: {weight:.2f} | Vote: {output}")

        # 2. Determine Winner
        if not weighted_votes:
            return [], 0.0
            
        best_pattern = max(weighted_votes, key=weighted_votes.get)
        winner_weight = weighted_votes[best_pattern]
        
        # 3. Calculate Confidence based on Weighted Majority
        confidence = (winner_weight / total_mesh_weight) * 100
        
        print(f"\n--- [RESULT] Consensus Reached ---")
        print(f"Decision: {list(best_pattern)}")
        print(f"Weighted Confidence: {confidence:.1f}%")
        
        return list(best_pattern), confidence

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    ensemble = WeightedEnsemble(db)
    
    # Simulate a Sybil Attack:
    # 1. One 'Whale' node (Honest, lots of DOPA)
    # 2. Five 'Sybil' nodes (Malicious, zero DOPA, trying to outvote)
    
    # Setup database records
    whale_id = "12D3KooW_HONEST_WHALE"
    db.update_peer(whale_id, spikes=1000, reward=5000.0) # High stake
    
    # Sybils have no history in DB (record will be None, getting default 1.0 weight)
    
    mock_outputs = {
        whale_id: [1, 0], # The 'Correct' inference
        "SYBIL_1": [0, 1],
        "SYBIL_2": [0, 1],
        "SYBIL_3": [0, 1],
        "SYBIL_4": [0, 1],
        "SYBIL_5": [0, 1],
    }
    
    decision, confidence = ensemble.get_consensus(mock_outputs)
    
    if decision == [1, 0]:
        print("\nSUCCESS: Weighted voting defeated the Sybil attack.")
    else:
        print("\nFAILURE: Sybil nodes successfully outvoted the whale.")

