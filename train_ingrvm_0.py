import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate
from snntorch import functional as SF
from torch.utils.data import DataLoader, TensorDataset
from quantization import BinaryLinear

# --- Hyperparameters ---
num_inputs = 3
num_hidden = 16
num_outputs = 2
beta = 0.95
num_steps = 10
batch_size = 16
learning_rate = 1e-3
num_epochs = 50 

# --- Model Architecture (Phase 3: 1-Bit 'Muscle') ---
class SentimentAlphaNet(nn.Module):
    def __init__(self):
        super().__init__()
        # Use a surrogate gradient for backprop through spikes
        spike_grad = surrogate.fast_sigmoid(slope=25)
        
        # 1-Bit Optimized Layers
        self.fc1 = BinaryLinear(num_inputs, num_hidden)
        self.lif1 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.fc2 = BinaryLinear(num_hidden, num_outputs)
        self.lif2 = snn.Leaky(beta=beta, spike_grad=spike_grad)

    def forward(self, x):
        # Initialize membrane potentials
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()
        
        spk2_rec = []
        
        # Temporal Loop
        for step in range(num_steps):
            cur1 = self.fc1(x)
            spk1, mem1 = self.lif1(cur1, mem1)
            cur2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur2, mem2)
            spk2_rec.append(spk2)
            
        return torch.stack(spk2_rec, dim=0) # Shape: (steps, batch, outputs)

# --- Training Logic ---
def train_model():
    print(f"--- Preparing 1-Bit Training Loop for 1080 Ti ---")
    
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    print(f"Current Device: {device}")
    
    model = SentimentAlphaNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    # Correct Functional Loss
    loss_fn = SF.ce_rate_loss() 

    # LOAD DATASET
    data_path = "ingrvms/sentiment_data.pt"
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}")
        return
        
    dataset = torch.load(data_path)
    x_train, y_train = dataset["x_train"], dataset["y_train"]
    x_test, y_test = dataset["x_test"], dataset["y_test"]
    
    train_ds = TensorDataset(x_train, y_train)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    test_ds = TensorDataset(x_test, y_test)
    test_loader = DataLoader(test_ds, batch_size=batch_size)

    print(f"Starting 1-Bit GPU Training for {num_epochs} epochs...")
    for epoch in range(num_epochs):
        loss_hist = []
        for data, targets in train_loader:
            data, targets = data.to(device), targets.to(device)
            
            # Forward pass
            spk_rec = model(data)
            
            # Loss calculation
            loss_val = loss_fn(spk_rec, targets)
            
            # Gradient descent
            optimizer.zero_grad()
            loss_val.backward()
            optimizer.step()
            
            loss_hist.append(loss_val.item())
        
        # Validation
        correct = 0
        total = 0
        with torch.no_grad():
            for data, targets in test_loader:
                data, targets = data.to(device), targets.to(device)
                spk_rec = model(data)
                predictions = spk_rec.sum(dim=0).argmax(dim=1)
                correct += (predictions == targets).sum().item()
                total += targets.size(0)
        
        accuracy = 100 * correct / total
        print(f"Epoch {epoch+1}: Avg Loss = {sum(loss_hist)/len(loss_hist):.4f} | Test Acc = {accuracy:.2f}%")

    # Save trained weights
    torch.save(model.state_dict(), "ingrvms/sentiment_alpha.pt")
    print(f"\nSUCCESS: 1-Bit Model trained and saved to ingrvms/sentiment_alpha.pt")

if __name__ == "__main__":
    import os
    train_model()
