import requests
import os
import sys

# Load env for Hub URL
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

HUB_URL = os.getenv("INGRVM_HUB_URL", "http://192.168.68.51:8000")

def test_upload():
    print(f"--- Testing Marketplace Upload to {HUB_URL} ---")
    
    # 1. Create a dummy weight file
    dummy_file = "mock_weights.pt"
    with open(dummy_file, "wb") as f:
        f.write(os.urandom(1024)) # 1KB of junk data
    
    # 2. Define metadata
    params = {
        "name": "Laptop Test INGRVM",
        "author_id": "LAPTOP_RELAY",
        "version": "0.0.1",
        "category": "Testing",
        "description": "A mock ingrvm uploaded from the laptop to test Phase 6 foundations.",
        "architecture": "BitNet-1bit"
    }
    
    # 3. Upload
    url = f"{HUB_URL}/api/marketplace/upload"
    try:
        with open(dummy_file, "rb") as f:
            files = {"file": (dummy_file, f, "application/octet-stream")}
            response = requests.post(url, params=params, files=files)
            
        if response.status_code == 200:
            print(f"✅ SUCCESS: {response.json()}")
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    test_upload()

