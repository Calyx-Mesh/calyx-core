import torch
import os
import sys
import json

def shard_model(model_path, shard_ranges):
    """
    Splits a PyTorch model state_dict into multiple shards based on layer names.
    
    shard_ranges: List of dicts [{"name": "shard1", "layers": ["fc1", "lif1"]}, ...]
    """
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        return

    print(f"--- 🔪 INGRVM Weight Sharder: {os.path.basename(model_path)} ---")
    
    try:
        state_dict = torch.load(model_path, map_location="cpu")
    except Exception as e:
        print(f"❌ Failed to load weights: {e}")
        return

    all_keys = list(state_dict.keys())
    print(f"Total parameters found: {len(all_keys)}")

    base_name = os.path.splitext(model_path)[0]

    for shard in shard_ranges:
        shard_dict = {}
        matched_keys = []
        
        for key in all_keys:
            # Check if any layer prefix in the range matches this key
            for layer_prefix in shard["layers"]:
                if key.startswith(layer_prefix):
                    shard_dict[key] = state_dict[key]
                    matched_keys.append(key)
                    break
        
        if shard_dict:
            shard_file = f"{base_name}_{shard['name']}.pt"
            torch.save(shard_dict, shard_file)
            print(f"✅ Saved Shard '{shard['name']}': {len(matched_keys)} layers -> {shard_file}")
        else:
            print(f"⚠️ No layers matched for shard: {shard['name']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python weight_sharder.py <model.pt>")
        # Example for sentiment_alpha
        # python weight_sharder.py ingrvms/sentiment_alpha.pt
    else:
        # Hardcoded example logic for Sentiment Alpha
        ranges = [
            {"name": "PC", "layers": ["fc1", "lif1"]},
            {"name": "LAPTOP", "layers": ["fc2", "lif2"]}
        ]
        shard_model(sys.argv[1], ranges)

