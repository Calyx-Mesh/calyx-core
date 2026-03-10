import sys
import os
import unittest

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from reward_validator import RewardValidator
from spike_sanitizer import SpikeSanitizer
from identity_manager import NodeIdentity
from spike_protocol import NeuralSpike

class TestINGRVMSecurity(unittest.TestCase):
    def setUp(self):
        self.validator = RewardValidator()
        self.sanitizer = SpikeSanitizer()
        # Use absolute or correctly relative path for the test key
        self.key_path = os.path.join(os.path.dirname(__file__), "test_node.key")
        self.identity = NodeIdentity(key_path=self.key_path)

    def tearDown(self):
        if os.path.exists(self.key_path):
            os.remove(self.key_path)

    def test_signature_validation(self):
        """ Test that signed spikes are verified and tampered ones are caught. """
        spike = NeuralSpike(
            task_id="T1", ingrvm_id="s0", 
            node_id=self.identity.get_public_key_b64(), 
            input_hash="h"
        )
        spike.set_spikes([1, 0, 1])
        
        # Sign
        spike.signature = None
        spike.signature = self.identity.sign_data(spike.to_bin())
        
        # Verify
        ok, msg = self.validator.verify_spike_integrity(spike)
        self.assertTrue(ok, f"Validation failed: {msg}")
        
        # Tamper
        spike.task_id = "TAMPERED"
        ok_bad, msg_bad = self.validator.verify_spike_integrity(spike)
        self.assertFalse(ok_bad, "Tampered spike was incorrectly accepted!")

    def test_spike_sanitization(self):
        """ Test that malicious values are neutralized to binary pulses. """
        toxic_input = [1.0, 0.0, float('nan'), 999999.0, float('-inf')]
        sanitized = self.sanitizer.sanitize(toxic_input)
        
        # Verify: All values must be 0 or 1
        for v in sanitized:
            self.assertIn(v, [0, 1])
        
        self.assertEqual(sanitized[2], 0) # NaN became 0
        self.assertEqual(sanitized[3], 1) # 999999 became 1 (clamped)

if __name__ == "__main__":
    unittest.main()

