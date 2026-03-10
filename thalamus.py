import trio
import json
import torch
import os
from typing import Dict, Any
from ingrvm_packager import ingrvmPackage
from train_ingrvm_0 import ingrvm0Net
from spike_protocol import NeuralSpike

class ThalamusRouter:
    """
    Orchestrates multiple 'ingrvms' on a single node.
    Routes incoming spikes to the correct local SNN brain.
    """
    def __init__(self):
        self.active_ingrvms: Dict[str, Any] = {}
        self.packager = ingrvmPackage("Thalamus")
        print("[THALAMUS] Central router initialized.")

    def register_ingrvm(self, ingrvm_id: str, brain_model: Any):
        self.active_ingrvms[ingrvm_id] = brain_model
        print(f"[THALAMUS] ingrvm '{ingrvm_id}' registered and ready.")

    def load_package(self, package_path: str):
        """Loads a .ingrvm package and registers the ingrvm."""
        print(f"[THALAMUS] Loading package: {package_path}")
        try:
            package = self.packager.unpack_package(package_path)
            ingrvm_id = package["ingrvm_id"]
            metadata = package["metadata"]
            weights_bytes = package["weights"]
            
            # Currently only supports ingrvm0Net (Sentiment Analysis)
            # Future: Use metadata to select architecture
            model = ingrvm0Net()
            
            # Load weights from binary buffer
            import io
            buffer = io.BytesIO(weights_bytes)
            model.load_state_dict(torch.load(buffer, map_location=torch.device('cpu')))
            model.eval() # Set to evaluation mode
            
            self.register_ingrvm(ingrvm_id, model)
            return True
        except Exception as e:
            print(f"[THALAMUS] ERROR loading package: {e}")
            return False

    async def route_spike(self, spike: NeuralSpike) -> Any:
        """
        Takes a NeuralSpike and sends it to the correct MiniBrain.
        """
        ingrvm_id = spike.ingrvm_id
        
        if ingrvm_id not in self.active_ingrvms:
            print(f"[THALAMUS] Error: ingrvm '{ingrvm_id}' not found locally.")
            return None
            
        print(f"[THALAMUS] Routing Task {spike.task_id} to ingrvm '{ingrvm_id}'")
        
        model = self.active_ingrvms[ingrvm_id]
        
        # 1. Convert spike data to tensor and add BATCH dimension [1, 3]
        input_data = torch.tensor(spike.get_spikes()).float().unsqueeze(0)
        
        # 2. Run Inference
        with torch.no_grad():
            output_spikes = model(input_data)
            # output_spikes shape: (steps, batch=1, outputs)
            # Sum over time (dim 0) to get final decision
            prediction = output_spikes.sum(dim=0).argmax(dim=1)
            
        return {
            "status": "PROCESSED",
            "task_id": spike.task_id,
            "ingrvm_id": ingrvm_id,
            "prediction": int(prediction.item()),
            "output_tensor": output_spikes.tolist()
        }

# --- Verification Test ---
if __name__ == "__main__":
    thalamus = ThalamusRouter()
    
    # Path to the trained package we created
    pkg_path = "neuromorphic_env/packages/ingrvm_0_trained.ingrvm"
    
    if os.path.exists(pkg_path):
        thalamus.load_package(pkg_path)
        
        # Mock an incoming spike
        # [0.5, 0.5, 0.5] -> should be Positive
        test_spike = NeuralSpike(
            task_id="TASK_PROD_001",
            ingrvm_id="ingrvm_0_sentiment_trained",
            node_id="LAPTOP_PROBE",
            input_hash="hash_123"
        )
        test_spike.set_spikes([0.5, 0.5, 0.5])
        
        async def test():
            result = await thalamus.route_spike(test_spike)
            print(f"\n[INFERENCE RESULT] Task {result['task_id']}: Prediction = {result['prediction']}")
            if result['prediction'] == 1:
                print("SUCCESS: Trained model correctly identified 'Positive' spike pattern.")
                
        trio.run(test)
    else:
        print(f"Error: {pkg_path} not found. Run pack_trained_ingrvm.py first.")
