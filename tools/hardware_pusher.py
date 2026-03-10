import time
import requests
import json
from hardware_monitor import HardwareProtector

# Configuration
HUB_URL = "http://localhost:8000/api/vitals"
PUSH_INTERVAL = 2 # Seconds

def push_vitals():
    """
    PC Side: Pushes hardware vitals from the 1080 Ti to the Hub.
    """
    monitor = HardwareProtector()
    print(f"🚀 Starting Hardware Pusher to {HUB_URL}...")

    while True:
        vitals = monitor.get_gpu_vitals()
        if vitals:
            try:
                # We only send what the Hub expects (GPUVitals model)
                payload = {
                    "temp": vitals['temp'],
                    "vram_used": vitals['vram_used'],
                    "vram_total": vitals['vram_total'],
                    "load": int(vitals['load']),
                    "psk": "INGRVM_SECURE_2026"
                }
                
                response = requests.post(HUB_URL, json=payload, timeout=2)
                if response.status_code == 200:
                    # Use \r to overwrite the line in terminal
                    print(f"📡 Sent Vitals: {vitals['temp']}C | {int(vitals['vram_used'])}MB used", end='\r')
                else:
                    print(f"⚠️ Hub Error: {response.status_code}")
            except Exception as e:
                print(f"❌ Connection Error: {e} - Retrying in 5s...")
                time.sleep(5)
        else:
            print("⚠️ No GPU detected. Check NVML/Drivers.", end='\r')
            
        time.sleep(PUSH_INTERVAL)

if __name__ == "__main__":
    try:
        push_vitals()
    except KeyboardInterrupt:
        print("\n🛑 Pusher stopped.")

