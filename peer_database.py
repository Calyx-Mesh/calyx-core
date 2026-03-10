import json
import os
import time
from typing import Dict, Optional
from pydantic import BaseModel

class PeerRecord(BaseModel):
    peer_id: str
    last_seen: float
    total_spikes_processed: int = 0
    reputation: float = 1.0 # 0.0 to 2.0
    tokens_earned: float = 0.0
    is_validator: bool = False

class PeerDatabase:
    """
    Persistent store for tracking network neighbors and their reliability.
    """
    def __init__(self, db_path: str = "neuromorphic_env/peer_db.json"):
        self.db_path = db_path
        self.peers: Dict[str, PeerRecord] = {}
        self.load()

    def load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                data = json.load(f)
                for pid, record in data.items():
                    self.peers[pid] = PeerRecord(**record)
            print(f"[PEER_DB] Loaded {len(self.peers)} records.")

    def save(self):
        with open(self.db_path, "w") as f:
            json.dump({pid: record.dict() for pid, record in self.peers.items()}, f, indent=4)

    def update_peer(self, peer_id: str, spikes: int = 0, reward: float = 0.0):
        if peer_id not in self.peers:
            self.peers[peer_id] = PeerRecord(peer_id=peer_id, last_seen=time.time())
        
        record = self.peers[peer_id]
        record.last_seen = time.time()
        record.total_spikes_processed += spikes
        record.tokens_earned += reward
        
        # Simple reputation growth: more work = more trust
        if spikes > 0:
            record.reputation = min(2.0, record.reputation + 0.005)
            
        self.save()

    def get_peer(self, peer_id: str) -> Optional[PeerRecord]:
        return self.peers.get(peer_id)

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    
    # Simulate discovering and rewarding a peer
    test_peer = "12D3KooW_MOCK_PEER_ALPHA"
    
    print(f"--- Peer Database Test ---")
    db.update_peer(test_peer, spikes=150, reward=12.5)
    
    record = db.get_peer(test_peer)
    if record:
        print(f"Peer: {record.peer_id[:12]}...")
        print(f"Reputation: {record.reputation:.3f}")
        print(f"Total $DOPA: {record.tokens_earned}")
        
    if os.path.exists("neuromorphic_env/peer_db.json"):
        print("\nSUCCESS: Peer database is persistent and functional.")

