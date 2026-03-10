import torch
import snntorch as snn
from snntorch import spikeplot as splot
import matplotlib.pyplot as plt

# Neuron parameters
beta = 0.95  # decay rate
num_steps = 100

# Initialize LIF neuron
lif1 = snn.Leaky(beta=beta)

# Create a sample input (constant current)
# Shape: (num_steps, batch_size, input_features)
input_current = torch.ones((num_steps, 1, 1)) * 0.5

# Arrays to store membrane potential and spikes
mem_rec = []
spk_rec = []

# Initialize membrane potential
mem = lif1.init_leaky()

# Simulation loop
for step in range(num_steps):
    spk, mem = lif1(input_current[step], mem)
    spk_rec.append(spk)
    mem_rec.append(mem)

# Convert to tensors
spk_rec = torch.stack(spk_rec)
mem_rec = torch.stack(mem_rec)

print(f"Simulation complete for {num_steps} steps.")
print(f"Total spikes generated: {int(spk_rec.sum())}")

# Optional: Print results for confirmation
if spk_rec.sum() > 0:
    print("SUCCESS: The neuron spiked! Virtual SNN logic is functional.")
else:
    print("The neuron did not spike. Try increasing input_current or beta.")
