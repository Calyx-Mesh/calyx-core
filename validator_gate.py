import torch
import torch.nn as nn
import snntorch as snn
import time
from ingrvm_packager import ingrvmPackage
from typing import Dict

# Define the model architecture globally for the validator to instantiate
class ingrvmNet(nn.Module):
    def __init__(self, layers_str: str):
        super().__init__()
        # Parsing "3-8-2"
        l = [int(x) for x in layers_str.split("-")]
        self.fc1 = nn.Linear(l[0], l[1])
        self.lif1 = snn.Leaky(beta=0.95)
        self.fc2 = nn.Linear(l[1], l[2])
        self.lif2 = snn.Leaky(beta=0.95)

    def forward(self, x):
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()
        spk2_rec = []
        for _ in range(5): # 5-step audit
            cur1 = self.fc1(x)
            spk1, mem1 = self.lif1(cur1, mem1)
            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)
            spk2_rec.append(spk2)
        return torch.stack(spk2_rec).sum(dim=0)

class ingrvmValidator:
    """
    Simulates a Tier II node's Pre-Frontal Cortex audit logic.
    """
    def audit_ingrvm(self, package_path: str) -> Dict:
        print(f"--- Starting Pre-Frontal Cortex Audit: {package_path} ---")
        packager = ingrvmPackage("validator_temp")
        unpacked = packager.unpack_package(package_path)
        
        # 1. Architecture Check
        meta = unpacked["metadata"]
        print(f"[AUDIT] Checking architecture: {meta['layers']}")
        
        # 2. Load and Instantiate
        model = ingrvmNet(meta["layers"])
        # Use an io.BytesIO buffer to load the weights from the binary data
        import io
        model.load_state_dict(torch.load(io.BytesIO(unpacked["weights"])))
        
        # 3. Stress Test (Inference Audit)
        print("[AUDIT] Running firing-rate stress test...")
        # Create 100 random samples
        audit_input = torch.randn((100, 3))
        
        start_time = time.time()
        with torch.no_grad():
            output_spikes = model(audit_input)
        end_time = time.time()
        
        # 4. Reputation Calculation
        avg_firing_rate = output_spikes.mean().item()
        audit_latency = (end_time - start_time) * 1000 # ms
        
        # Metric: Good models fire reliably but efficiently
        # Score 0-100 based on latency and firing range
        reputation_score = 100 - (audit_latency * 2) 
        if avg_firing_rate == 0: reputation_score -= 50 # Model is dead/silent
        
        print(f"[AUDIT] Avg Firing Rate: {avg_firing_rate:.2f}")
        print(f"[AUDIT] Latency: {audit_latency:.2f}ms")
        print(f"[AUDIT] Initial Reputation Score: {reputation_score:.1f}/100")
        
        return {
            "reputation": reputation_score,
            "latency_ms": audit_latency,
            "status": "APPROVED" if reputation_score > 50 else "REJECTED"
        }

# --- Verification Test ---
if __name__ == "__main__":
    validator = ingrvmValidator()
    pkg_path = "neuromorphic_env/packages/ingrvm_0.ingrvm"
    
    result = validator.audit_ingrvm(pkg_path)
    print(f"\n--- AUDIT FINAL RESULT: {result['status']} ---")
