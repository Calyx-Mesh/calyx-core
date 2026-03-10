import sys
import os
import json

# Add parent to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zk_proof_generator import ZKProofGenerator
from spike_protocol import NeuralSpike

def verify_spike_poi(spike_bin_path: str):
    """
    Loads a binary spike file and verifies its zk-PoI packet.
    """
    if not os.path.exists(spike_bin_path):
        print(f"❌ File not found: {spike_bin_path}")
        return

    with open(spike_bin_path, "rb") as f:
        data = f.read()
    
    try:
        spike = NeuralSpike.from_bin(data)
    except Exception as e:
        print(f"❌ Failed to parse spike: {e}")
        return

    print(f"--- 🛡️ Verifying PoI for Task: {spike.task_id[:8]} ---")
    print(f"Node: {spike.node_id}")
    print(f"Layer: {spike.current_layer}")

    if not hasattr(spike, 'poi_packet') or not spike.poi_packet:
        print("❌ ERROR: No PoI packet found in spike.")
        return

    zk = ZKProofGenerator()
    is_valid = zk.verify_poi(spike.poi_packet, spike.model_name)

    if is_valid:
        print("✅ SUCCESS: zk-Proof of Inference is valid.")
        print(f"Merkle Root: {spike.poi_packet['proof']['merkle_root'][:16]}...")
    else:
        print("❌ FAILED: Proof verification failed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_poi.py <spike_file.bin>")
    else:
        verify_spike_poi(sys.argv[1])
