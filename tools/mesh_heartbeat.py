import trio
import json
import os
import sys
import time
import requests
import psutil
import socket
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add core to path for imports
core_dir = Path(__file__).parent.parent
sys.path.append(str(core_dir))

from config import INGRVMConfig

class MeshHeartbeat:
    """
    Phase 10 Task: Outbound Mesh Heartbeat.
    Broadcasts local hardware tier and vitals to the INGRVM Hub.
    """
    def __init__(self):
        self.conf = INGRVMConfig()
        # Find root directory (where neuromorphic_env usually lives)
        self.root = Path(__file__).parent.parent.parent.parent.absolute()
        self.env_dir = self.core_dir_check()
        
        load_dotenv(self.root / "INGRVM" / ".env")
        
        self.hub_url = os.getenv("INGRVM_HUB_URL", self.conf.get("node", "hub_url"))
        self.node_id = os.getenv("INGRVM_NODE_ID", "LAPTOP_RELAY")
        
        self.tier_file = self.env_dir / "hardware_tier.json"
        self.hardware_tier = self._load_tier()

    def core_dir_check(self) -> Path:
        """ Robust check for neuromorphic_env location. """
        possible = [
            Path("neuromorphic_env"),
            Path("INGRVM/Core/neuromorphic_env"),
            Path("../neuromorphic_env"),
            Path("../../neuromorphic_env")
        ]
        for p in possible:
            if p.exists():
                return p.absolute()
        return Path("neuromorphic_env")

    def _load_tier(self) -> int:
        if self.tier_file.exists():
            try:
                with open(self.tier_file, "r") as f:
                    data = json.load(f)
                    return data.get("tier", 3)
            except Exception: pass
        return 3 # Default to Standard

    def get_vitals(self) -> dict:
        return {
            "node_id": self.node_id,
            "tier": self.hardware_tier,
            "cpu_load": psutil.cpu_percent(),
            "ram_usage": psutil.virtual_memory().percent,
            "timestamp": time.time(),
            "local_ip": socket.gethostbyname(socket.gethostname())
        }

    async def run(self, interval=30):
        print(f"--- 💓 INGRVM Outbound Heartbeat Active ---")
        print(f"Target Hub: {self.hub_url}")
        print(f"Node ID:    {self.node_id}")
        print(f"Tier:       {self.hardware_tier}")
        
        while True:
            vitals = self.get_vitals()
            try:
                endpoint = f"{self.hub_url}/api/mesh/log"
                payload = {
                    "node_id": self.node_id,
                    "event": "HEARTBEAT",
                    "data": vitals,
                    "t": datetime.datetime.now().isoformat() + "Z"
                }

                resp = requests.post(endpoint, json=payload, timeout=5)
                if resp.status_code == 200:
                    print(f"[{time.strftime('%H:%M:%S')}] 💓 Heartbeat Delivered.")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Hub returned {resp.status_code}")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Hub Unreachable: {e}")
            
            await trio.sleep(interval)

if __name__ == "__main__":
    hb = MeshHeartbeat()
    try:
        trio.run(hb.run)
    except KeyboardInterrupt:
        print("\n🛑 Heartbeat stopped.")
