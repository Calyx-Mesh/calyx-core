import torch
import torch.nn as nn
import snntorch as snn
from collections import Counter
from typing import List

# --- The Brain Architecture ---
num_inputs, num_hidden, num_outputs = 3, 8, 2
beta, vth = 0.99, 0.5

class MiniBrain(nn.Module):
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id
        self.fc1 = nn.Linear(num_inputs, num_hidden)
        self.lif1 = snn.Leaky(beta=beta, threshold=vth)
        self.fc2 = nn.Linear(num_hidden, num_outputs)
        self.lif2 = snn.Leaky(beta=beta, threshold=vth)
        
        # Initialize membrane states
        self.mem1 = self.lif1.init_leaky()
        self.mem2 = self.lif2.init_leaky()

    def forward(self, x):
        cur1 = self.fc1(x)
        spk1, self.mem1 = self.lif1(cur1, self.mem1)
        cur2 = self.fc2(spk1)
        spk2, self.mem2 = self.lif2(cur2, self.mem2)
        return spk2

class NeuralEnsemble:
    """
    Simulates a cluster of nodes processing the same task to reach consensus.
    """
    def __init__(self, num_nodes: int = 3):
        # Create multiple instances of the same architecture, but with slightly 
        # different random weights to simulate different 'ingrvm' shards or node states.
        self.nodes = [MiniBrain(f"NODE_{i}") for i in range(num_nodes)]

    def process_task(self, input_data: List[int]) -> List[int]:
        print(f"--- Ensemble Processing Started (Nodes: {len(self.nodes)}) ---")
        input_tensor = torch.tensor(input_data).float()
        
        results = []
        for node in self.nodes:
            output_spk = node(input_tensor)
            # Convert binary spikes to a 'Decision' (e.g., index of the firing neuron)
            decision = output_spk.tolist()
            results.append(tuple(decision))
            print(f"[{node.node_id}] Produced Output: {decision}")

        # --- Consensus Logic: Majority Vote ---
        vote_count = Counter(results)
        consensus_result, count = vote_count.most_common(1)[0]
        
        confidence = (count / len(self.nodes)) * 100
        print(f"\n--- Consensus Reached ---")
        print(f"Final Decision: {list(consensus_result)}")
        print(f"Confidence: {confidence:.1f}%")
        
        if confidence < 60.0:
            print("WARNING: Low consensus. Network might be hallucinating.")
            
        return list(consensus_result)

# --- Verification Test ---
if __name__ == "__main__":
    ensemble = NeuralEnsemble(num_nodes=5) # 5-node swarm
    
    # Strong input to trigger firing
    test_input = [5, 5, 5]
    
    ensemble.process_task(test_input)
