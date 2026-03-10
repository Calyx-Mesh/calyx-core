# INGRVM Mesh: Laptop Launch Script (Probe)
Write-Host "--- Launching THOR INGRVM Mesh (Laptop Side) ---" -ForegroundColor Yellow

# 1. Sync latest logic from PC
Write-Host "[1/2] Pulling latest mesh logic..."
git pull

# 2. Run the Spike Sender
Write-Host "[2/2] Initiating 1-bit Neural Probe..."
python neuromorphic_env/spike_sender.py

Write-Host "Probe complete." -ForegroundColor Green
Pause
