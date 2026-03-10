import torch
import os

def generate_mock_dataset(num_samples: int = 1000):
    """
    Generates a synthetic sentiment dataset for SNN training.
    Inputs: 3 normalized ASCII features.
    Targets: 0 (Negative), 1 (Positive).
    """
    print(f"--- Generating Mock Sentiment Dataset ({num_samples} samples) ---")
    
    # Generate random features
    x_data = torch.randn((num_samples, 3))
    
    # Create a simple rule: if sum of features > 0, it's Positive
    y_data = (x_data.sum(dim=1) > 0).long()
    
    dataset = {
        "x_train": x_data[:800],
        "y_train": y_data[:800],
        "x_test": x_data[800:],
        "y_test": y_data[800:]
    }
    
    output_path = "neuromorphic_env/ingrvms/sentiment_data.pt"
    torch.save(dataset, output_path)
    
    print(f"SUCCESS: Dataset saved to {output_path}")
    print(f"Distribution: {int(y_data.sum())} Positive, {num_samples - int(y_data.sum())} Negative")

if __name__ == "__main__":
    if not os.path.exists("neuromorphic_env/ingrvms"):
        os.makedirs("neuromorphic_env/ingrvms")
    generate_mock_dataset()
