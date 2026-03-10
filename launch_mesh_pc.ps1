# INGRVM Mesh: PC Launch Script (Main Neuron)
Write-Host "--- Launching THOR INGRVM Mesh (PC Side) ---" -ForegroundColor Cyan

# 1. Start the Lighthouse (Relay) in a new window
Write-Host "[1/2] Starting Lighthouse Relay..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python neuromorphic_env/bootstrap_beacon.py"

# 2. Start the Neural Node (GPU) in a new window
Write-Host "[2/2] Starting Neural Node (1080 Ti)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python neuromorphic_env/neural_node.py"

Write-Host "Mesh is active. Waiting for Laptop connection..." -ForegroundColor Green
