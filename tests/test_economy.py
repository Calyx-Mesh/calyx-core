import sys
import os
import unittest

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from reward_engine import RewardEngine
from slashing_protocol import SlashingManager
from peer_database import PeerDatabase

class TestINGRVMEconomy(unittest.TestCase):
    def setUp(self):
        # Use absolute path for test DB
        self.db_path = os.path.join(os.path.dirname(__file__), "test_peer_db.json")
        self.db = PeerDatabase(db_path=self.db_path)
        self.engine = RewardEngine(epoch_emission=100.0)
        self.slasher = SlashingManager(self.db)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_reward_distribution(self):
        """ Test that rewards are calculated correctly based on work and reputation. """
        self.engine.register_work("node_a", spikes=1000)
        self.engine.nodes["node_a"].reputation_score = 1.0
        
        self.engine.register_work("node_b", spikes=500)
        self.engine.nodes["node_b"].reputation_score = 1.0
        
        payouts = self.engine.calculate_payouts()
        
        self.assertIn("node_a", payouts)
        # Node A did 2x work, so should get 2x reward
        self.assertAlmostEqual(payouts["node_a"], 66.6667, places=2)
        self.assertAlmostEqual(sum(payouts.values()), 100.0, places=2)

    def test_slashing_logic(self):
        """ Test that reputation is deducted for bad behavior. """
        target = "test_bad_node"
        self.db.update_peer(target, spikes=100, reward=100.0)
        
        initial_rep = self.db.get_peer(target).reputation
        self.slasher.slash_node(target, "TEST_PENALTY", severity=0.5)
        
        new_rep = self.db.get_peer(target).reputation
        self.assertLess(new_rep, initial_rep)

if __name__ == "__main__":
    unittest.main()

