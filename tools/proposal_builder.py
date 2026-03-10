import json
import time
import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from identity_manager import NodeIdentity

class ProposalBuilder:
    """
    Standardizes the creation of INGRVM Governance Proposals.
    Every proposal must be signed by the architect/proposer.
    """
    def __init__(self, identity: NodeIdentity):
        self.identity = identity

    def create_proposal(self, title: str, description: str, action: str):
        proposal = {
            "title": title,
            "description": description,
            "action": action,
            "timestamp": time.time(),
            "proposer": self.identity.get_public_key_b64(),
            "signature": None
        }
        
        # Sign the JSON string
        payload = json.dumps(proposal, sort_keys=True).encode()
        proposal["signature"] = self.identity.sign_data(payload)
        
        print(f"--- 📜 PROPOSAL CREATED: {title} ---")
        return proposal

# --- Verification Test ---
if __name__ == "__main__":
    id = NodeIdentity()
    builder = ProposalBuilder(id)
    
    prop = builder.create_proposal(
        title="INGRVM_EXPANSION_01",
        description="Double the rewards for Type B Neural Shards.",
        action="SET_REWARD_EMISSION 200.0"
    )
    
    if prop["signature"]:
        print("\nSUCCESS: Governance proposal signed and ready for DAO vote.")

