import unittest
import torch
import sys
import os

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from quantization import NeuromorphicQuantizer, BinaryLinear
from tools.hardware_monitor import HardwareProtector

class TestPCCore(unittest.TestCase):
    """
    Unit Tests for INGRVM Phase 2 PC Core Logic.
    """
    def test_bit_packing(self):
        """ Tests if bit_pack and bit_unpack are lossless for 1-bit values. """
        q = NeuromorphicQuantizer()
        original = torch.sign(torch.randn(100))
        packed = q.bit_pack(original)
        unpacked = q.bit_unpack(packed, original.shape)
        
        self.assertTrue(torch.equal(original, unpacked))
        self.assertEqual(packed.numel(), 13) # 100 bits = 13 bytes (with padding)

    def test_binary_linear_forward(self):
        """ Tests the forward pass of the 1-bit linear layer. """
        layer = BinaryLinear(10, 5)
        input_data = torch.randn(2, 10)
        output = layer(input_data)
        
        self.assertEqual(output.shape, (2, 5))
        self.assertFalse(torch.isnan(output).any())

    def test_hardware_monitor_presence(self):
        """ Tests if the hardware monitor can at least initialize. """
        monitor = HardwareProtector()
        self.assertIsNotNone(monitor)

if __name__ == "__main__":
    unittest.main()

