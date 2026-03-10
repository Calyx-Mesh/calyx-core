import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate
import os
import sys

# Add parent dir to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from quantization import BinaryLinear

class SentimentAlpha:
    """
    Phase 3: Sentiment Alpha Inference Engine.
    Uses 1-bit weights and SNN logic for ultra-efficient text analysis.
    """
    def __init__(self, weights_path="ingrvms/sentiment_alpha.pt"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.num_inputs = 3
        self.num_hidden = 16
        self.num_outputs = 2
        self.beta = 0.95
        self.num_steps = 10
        
        # 1. Build Architecture
        spike_grad = surrogate.fast_sigmoid(slope=25)
        self.fc1 = BinaryLinear(self.num_inputs, self.num_hidden)
        self.lif1 = snn.Leaky(beta=self.beta, spike_grad=spike_grad, init_hidden=True)
        self.fc2 = BinaryLinear(self.num_hidden, self.num_outputs)
        self.lif2 = snn.Leaky(beta=self.beta, spike_grad=spike_grad, init_hidden=True)
        
        # 2. Move to Device
        self.fc1.to(self.device)
        self.lif1.to(self.device)
        self.fc2.to(self.device)
        self.lif2.to(self.device)
        
        # 3. Load Weights (if they exist)
        full_weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", weights_path))
        if os.path.exists(full_weights_path):
            try:
                # Manual state dict loading to match named layers
                state_dict = torch.load(full_weights_path, map_location=self.device)
                self.fc1.load_state_dict({"weight": state_dict["fc1.weight"], "bias": state_dict["fc1.bias"]})
                self.fc2.load_state_dict({"weight": state_dict["fc2.weight"], "bias": state_dict["fc2.bias"]})
                # LIF layers don't have learnable weights usually, but we sync beta if needed
                self.lif1.beta = state_dict.get("lif1.beta", self.beta)
                self.lif2.beta = state_dict.get("lif2.beta", self.beta)
                print(f"[LOAD] Loaded Sentiment Alpha weights from {weights_path}")
            except Exception as e:
                print(f"[WARN] Failed to load weights: {e}. Using untrained random weights.")

        else:
            print(f"[INFO] Weights not found at {full_weights_path}. Running with random 1-bit weights.")

    def tokenize(self, text: str) -> torch.Tensor:
        """
        Simple 3-dim tokenizer for Sentiment Alpha.
        Maps text to [length, polarity_seed, frequency_seed].
        """
        text = text.lower()
        length = min(1.0, len(text) / 50.0)
        
        # Mock sentiment vectors based on keywords
        pos_words = ["good", "great", "love", "happy", "yes", "up"]
        neg_words = ["bad", "hate", "sad", "down", "no", "fail"]
        
        pos_count = sum(1 for w in pos_words if w in text)
        neg_count = sum(1 for w in neg_words if w in text)
        
        polarity = (pos_count - neg_count) / 5.0
        frequency = text.count(' ') / 10.0
        
        return torch.tensor([length, polarity, frequency], dtype=torch.float32).to(self.device)

    def infer(self, text: str) -> dict:
        """
        Runs neuromorphic inference on the input text.
        """
        x = self.tokenize(text).unsqueeze(0) # Batch size 1
        
        # Reset neuron state
        self.lif1.init_leaky()
        self.lif2.init_leaky()
        
        spk_rec = []
        with torch.no_grad():
            for _ in range(self.num_steps):
                cur1 = self.fc1(x)
                spk1 = self.lif1(cur1)
                cur2 = self.fc2(spk1)
                spk2 = self.lif2(cur2)
                spk_rec.append(spk2)
        
        # Sum spikes over time
        final_spks = torch.stack(spk_rec).sum(dim=0)
        prediction = final_spks.argmax(dim=1).item()
        confidence = (final_spks.max() / self.num_steps).item() * 100
        
        label = "POSITIVE" if prediction == 1 else "NEGATIVE"
        
        return {
            "text": text,
            "sentiment": label,
            "confidence": f"{confidence:.1f}%",
            "spikes": int(final_spks.sum().item())
        }

if __name__ == "__main__":
    engine = SentimentAlpha()
    test_cases = [
        "I love this neuromorphic mesh!",
        "The GPU is running too hot, I hate it.",
        "System is operational and ready."
    ]
    
    print("\n--- Sentiment Alpha Inference Test ---")
    for text in test_cases:
        res = engine.infer(text)
        print(f"[{res['sentiment']}] ({res['confidence']}) Text: {text}")
