import torch
import random
import copy
from typing import List, Dict

class EvolutionEngine:
    """
    Simulates the 'Breeding' of better AI ingrvms.
    Takes a population of SNNs and evolves them based on Reputation.
    """
    def __init__(self, mutation_rate: float = 0.05):
        self.mutation_rate = mutation_rate

    def breed(self, parent_a_weights: Dict, parent_b_weights: Dict) -> Dict:
        """Combines weights of two parents (Crossover)."""
        child_weights = copy.deepcopy(parent_a_weights)
        
        for key in child_weights.keys():
            # 50/50 chance to take from parent B
            if random.random() > 0.5:
                child_weights[key] = parent_b_weights[key]
                
            # Random Mutation (ONLY for floating point parameters)
            if torch.is_floating_point(child_weights[key]):
                mutation_noise = torch.randn(child_weights[key].shape) * self.mutation_rate
                child_weights[key] += mutation_noise
            
        return child_weights

# --- Verification Test ---
if __name__ == "__main__":
    from neural_node import MiniBrain
    
    engine = EvolutionEngine()
    
    # 1. Create two 'Parent' brains
    parent_a = MiniBrain()
    parent_b = MiniBrain()
    
    print("--- Starting Genetic Evolution Test ---")
    
    # 2. Breed a 'Child' brain
    child_weights = engine.breed(parent_a.state_dict(), parent_b.state_dict())
    
    # 3. Load into a new brain
    child_brain = MiniBrain()
    child_brain.load_state_dict(child_weights)
    
    # Verify that child weights are unique (mutated)
    diff = torch.sum(child_brain.fc1.weight - parent_a.fc1.weight)
    
    if diff != 0:
        print(f"SUCCESS: Child genome evolved. Weight delta: {diff.item():.4f}")
    else:
        print("Evolution failed. Child is identical to parent.")
