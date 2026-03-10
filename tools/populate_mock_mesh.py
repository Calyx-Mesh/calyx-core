import sys
import os
import random

# Add parent dir to path so we can import peer_database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from peer_database import PeerDatabase

def populate():
    db = PeerDatabase(db_path="INGRVM/Core/peer_db.json")
    
    locations = ["Zilker", "Barton", "Rainey", "Domain", "Mueller", "East6th", "Congress", "HydePark"]
    descriptors = ["Firefly", "Seedling", "Nerve", "Sprout", "Bloom", "Root", "Vine", "Leaf"]
    
    print("--- Populating Austin Genesis Mesh Mockup ---")
    
    for i in range(25):
        loc = random.choice(locations)
        desc = random.choice(descriptors)
        peer_name = f"ATX_{loc}_{desc}_{random.randint(100, 999)}"
        
        # Random but realistic stats
        reputation = round(random.uniform(0.8, 1.95), 3)
        tokens = round(random.uniform(10.0, 500.0), 4)
        spikes = random.randint(1000, 50000)
        
        db.update_peer(peer_name, spikes=spikes, reward=tokens)
        db.peers[peer_name].reputation = reputation
        
    db.save()
    print(f"SUCCESS: 25 mock nodes added to the mesh database.")

if __name__ == "__main__":
    populate()

