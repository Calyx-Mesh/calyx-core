import torch
import trio
import os
import sys
from encoder import TextSpikeEncoder
from efficiency_monitor import EfficiencyMonitor
from neural_node import MiniBrain

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

class INGRVMPlayground:
    """
    The ultimate end-to-end demo of the INGRVM 'Virtual Seed'.
    Bridges human text -> spikes -> brain -> decision -> energy metrics.
    """
    def __init__(self):
        self.encoder = TextSpikeEncoder(num_steps=10)
        self.brain = MiniBrain()
        self.monitor = EfficiencyMonitor()
        
        # Initialize membrane states
        self.mem1 = self.brain.lif1.init_leaky()
        self.mem2 = self.brain.lif2.init_leaky()

    def process_input(self, text: str):
        print_f(f"\n--- [INPUT] '{text}' ---")
        
        # 1. Encoding
        spike_train = self.encoder.encode(text) # Shape: (steps, characters)
        print_f(f"[SENSORY] Encoded to {spike_train.shape[0]} temporal steps.")
        
        # 2. Brain Processing (Inference)
        total_spikes = 0
        
        # Reset membrane for new sentence
        self.mem1 = self.brain.lif1.init_leaky()
        self.mem2 = self.brain.lif2.init_leaky()
        
        fired_count = 0
        
        # Neuromorphic Loop: Process each time step
        for step in range(spike_train.shape[0]):
            # Get spikes for all characters at this time step
            # Our brain expects num_inputs=3. We'll take the first 3 characters 
            # or pad with zeros if text is shorter.
            input_data = torch.zeros(3)
            chars_to_read = min(len(text), 3)
            input_data[:chars_to_read] = spike_train[step, :chars_to_read]
            
            # Single-step inference
            final_spk, self.mem1, self.mem2 = self.brain(input_data, self.mem1, self.mem2)
            
            total_spikes += final_spk.sum().item()
            if final_spk.sum() > 0:
                fired_count += 1

        # 3. Decision Logic
        final_sentiment = "POSITIVE" if fired_count > 0 else "NEGATIVE"

        # 4. Energy Audit
        energy_stats = self.monitor.calculate_savings(3, 8, 2, int(total_spikes))

        print_f(f"[BRAIN] Spikes Generated: {int(total_spikes)}")
        print_f(f"[BRAIN] Decision: {final_sentiment}")
        print_f(f"[SOLARPUNK] Energy Reduction: {energy_stats['reduction_pct']}%")
        print_f(f"[SOLARPUNK] Joules Saved: {energy_stats['joules_saved']} J")

def main():
    playground = INGRVMPlayground()
    print_f("--- Welcome to the INGRVM Local Playground ---")
    
    # Pre-defined test sentences
    tests = ["YES", "NO", "Bio"]
    
    for t in tests:
        playground.process_input(t)
        
    print_f("\n--- Demo Complete. Ready for live input on PC. ---")

if __name__ == "__main__":
    main()
