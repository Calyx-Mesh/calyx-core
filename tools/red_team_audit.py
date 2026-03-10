import sys
import os
import time

# Add Core to path for reward_engine and governance_dao
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from reward_engine import INGRVMLedger
from governance_dao import INGRVMDAO
from config import INGRVMConfig

class RedTeamAudit:
    """
    Task #15: Red-Team Simulation.
    Stress-tests the mesh for PoI spoofing and DAO flooding.
    """
    def __init__(self, ledger: INGRVMLedger, dao: INGRVMDAO):
        self.ledger = ledger
        self.dao = dao

    def run_spoofing_test(self, malicious_node="MALICIOUS_GHOST"):
        """ Simulates a node reporting fake work to get rewards. """
        print(f"--- 🧨 Attack: PoI Spoofing ({malicious_node}) ---")
        # In a real setup, this would fail at the 'hub_server.py' PoI check.
        # Here we verify the slash_node logic.
        self.ledger.slash_node(malicious_node, penalty_syn=10.0, rep_burn=0.5, memo="PoI Spoofing Detected")
        
        final_rep = self.ledger.get_reputation(malicious_node)
        if final_rep < 1.0:
            print(f"✅ SUCCESS: Malicious node burned (Rep: {final_rep:.2f}).")
        else:
            print("❌ FAILED: Slashing system ineffective.")

    def run_dao_flooding_test(self, malicious_node="DAO_SPAMMER"):
        """ Simulates a node trying to flood the DAO with proposals. """
        print(f"\n--- 🧨 Attack: DAO Flooding ({malicious_node}) ---")
        # Initialize spammer with low reputation
        self.ledger.record_work(malicious_node, spikes=1) # Low rep starts at 1.0, but we need it < 0.8
        # Burn reputation manually to simulate a previously caught attacker
        self.ledger.slash_node(malicious_node, penalty_syn=0, rep_burn=0.5) 
        
        # Try to create proposal
        p_id = self.dao.create_proposal(
            malicious_node, 
            "SET economy.spike_cost_joules TO 0.0", 
            "ingrvm_alpha", 
            "fake_hash"
        )
        
        if p_id is None:
            print("✅ SUCCESS: DAO correctly rejected proposal due to low reputation.")
        else:
            print("❌ FAILED: DAO flood protection bypassed.")

if __name__ == "__main__":
    ledger = INGRVMLedger(db_path="../neuromorphic_env/ledger.db")
    dao = INGRVMDAO(ledger, INGRVMConfig(), db_path="../neuromorphic_env/governance.db")
    audit = RedTeamAudit(ledger, dao)
    
    audit.run_spoofing_test()
    audit.run_dao_flooding_test()
