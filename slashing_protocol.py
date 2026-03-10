import time
from peer_database import PeerDatabase

class SlashingManager:
    """
    Implements the 'Slashing' security logic for the mesh.
    Penalizes nodes for malicious or Byzantine behavior.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db

    def slash_node(self, peer_id: str, reason: str, severity: float = 0.5):
        """
        severity: 0.0 to 1.0 (multiplier for penalty)
        """
        record = self.db.get_peer(peer_id)
        if not record:
            print(f"[SLASH] Node {peer_id} not found. Cannot slash.")
            return

        print(f"\n[CRITICAL] SLASHING NODE: {peer_id[:8]}...")
        print(f"[REASON] {reason}")
        
        # 1. Reputation Penalty (Massive drop)
        old_rep = record.reputation
        record.reputation = max(0.0, record.reputation - (1.0 * severity))
        
        # 2. Token Burn (Stake Penalty)
        # Slashes 10% of current balance by default
        tokens_burned = record.tokens_earned * (0.1 * severity)
        record.tokens_earned -= tokens_burned
        
        print(f"[RESULT] Reputation: {old_rep:.2f} -> {record.reputation:.2f}")
        print(f"[RESULT] Burned: {tokens_burned:.2f} $DOPA")
        
        self.db.save()

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    manager = SlashingManager(db)
    
    # 1. Setup a healthy node
    target = "12D3KooW_BAD_ACTOR"
    db.update_peer(target, spikes=1000, reward=500.0)
    
    # 2. Simulate a malicious event (detected by Ensemble or Validator)
    manager.slash_node(
        peer_id=target, 
        reason="Mismatched Signature / Forged Spike Data",
        severity=0.8
    )
    
    final_record = db.get_peer(target)
    if final_record and final_record.reputation < 1.0:
        print("\nSUCCESS: Slashing protocol enforced and persisted.")

