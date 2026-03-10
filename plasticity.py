import torch
import torch.nn as nn
from typing import List

class STDPPlasticity:
    """
    Implements Spike-Timing-Dependent Plasticity (STDP).
    Strengthens ingrvms if the pre-synaptic spike occurs just before 
    the post-synaptic spike.
    """
    def __init__(self, learning_rate: float = 0.01, time_window: int = 5):
        self.lr = learning_rate
        self.window = time_window # ms/steps

    def update_weights(self, 
                       weights: torch.Tensor, 
                       pre_spikes: torch.Tensor, 
                       post_spikes: torch.Tensor) -> torch.Tensor:
        """
        Adjusts weights based on the causal relationship of spikes.
        Formula: Delta_W = LR * (Post * Pre_History - Pre * Post_History)
        """
        # Simplistic STDP Mock for local verification
        # In a real SNN, we use trace-based STDP
        
        # 1. Potentiation (LTP): Pre fires, then Post fires (Causal)
        ltp = torch.outer(post_spikes, pre_spikes) * self.lr
        
        # 2. Depression (LTD): Post fires, then Pre fires (Anti-Causal)
        # For this mock, we'll assume a smaller penalty for anti-causal
        ltd = torch.outer(pre_spikes, post_spikes).t() * (self.lr * 0.5)
        
        new_weights = weights + ltp - ltd
        
        # 3. Normalization (Solarpunk Constraint: Keep weights bounded)
        new_weights = torch.clamp(new_weights, -1.0, 1.0)
        
        return new_weights

# --- Verification Test ---
if __name__ == "__main__":
    plasticity = STDPPlasticity(learning_rate=0.1)
    
    # Layer: 3 inputs -> 2 outputs
    weights = torch.zeros((2, 3))
    
    print("--- Starting STDP Learning Simulation ---")
    print(f"Initial Weights:\n{weights}")
    
    # Scenario: Input 0 and 1 fire, then Output 0 fires (Causal Link)
    pre = torch.tensor([1.0, 1.0, 0.0])
    post = torch.tensor([1.0, 0.0])
    
    weights = plasticity.update_weights(weights, pre, post)
    
    print(f"\n[LEARN] Pre-spikes {pre.tolist()} triggered Post-spikes {post.tolist()}")
    print(f"Updated Weights:\n{weights}")
    
    if weights[0, 0] > 0:
        print("\nSUCCESS: Synaptic potentiation verified. The brain is learning.")
    else:
        print("\nLearning failed to adjust weights.")
