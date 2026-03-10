import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

class INGRVMConfig:
    """
    Central Nervous System for Node Configuration.
    Loads settings from environment variables, then 'ingrvm_config.json', then defaults.
    Ensures all modules share the same DNA.
    """
    DEFAULTS = {
        "node": {
            "p2p_port": int(os.getenv("INGRVM_P2P_PORT", 60001)),
            "discovery_port": int(os.getenv("INGRVM_DISCOVERY_PORT", 60002)),
            "api_port": int(os.getenv("INGRVM_API_PORT", 8000)),
            "bootstrap_peers": os.getenv("INGRVM_BOOTSTRAP_PEERS", "").split(",") if os.getenv("INGRVM_BOOTSTRAP_PEERS") else [],
            "hub_url": os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")
        },
        "brain": {
            "layers": [3, 8, 2],
            "beta": 0.95,
            "threshold": 1.0,
            "stdp_learning_rate": 0.01
        },
        "economy": {
            "spike_cost_joules": float(os.getenv("INGRVM_SPIKE_COST", 0.05)),
            "max_energy_joules": float(os.getenv("INGRVM_MAX_ENERGY", 100.0)),
            "solar_recovery_rate": 2.0
        },
        "security": {
            "min_reputation": float(os.getenv("INGRVM_MIN_REPUTATION", 0.5)),
            "max_queue_size": 100,
            "slashing_severity": 0.5
        },
        "paths": {
            "ingrvms_dir": os.getenv("INGRVM_DOPAAPSES_DIR", "neuromorphic_env/ingrvms"),
            "packages_dir": os.getenv("INGRVM_PACKAGES_DIR", "neuromorphic_env/packages"),
            "identity_file": os.getenv("INGRVM_IDENTITY_FILE", "neuromorphic_env/identity.key"),
            "peer_db": os.getenv("INGRVM_PEER_DB", "neuromorphic_env/peer_db.json")
        }
    }

    def __init__(self, config_path: str = "ingrvm_config.json"):
        self.config_path = config_path
        self.settings = self.DEFAULTS.copy()
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    user_settings = json.load(f)
                    # Deep update logic could go here, for now simple override
                    self.settings.update(user_settings)
                print(f"[CONFIG] Loaded settings from {self.config_path}")
            except Exception as e:
                print(f"[CONFIG] Error loading file: {e}. Using defaults.")
        else:
            print("[CONFIG] No config file found. Using default DNA.")
            self.save() # Generate the file for the user

    def save(self):
        with open(self.config_path, "w") as f:
            json.dump(self.settings, f, indent=4)
        print(f"[CONFIG] Generated default configuration file.")

    def get(self, section: str, key: str) -> Any:
        return self.settings.get(section, {}).get(key)

    def set(self, section: str, key: str, value: Any):
        """ Task #15: Dynamically update a parameter and save to disk. """
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save()
        print(f"[CONFIG] Parameter {section}.{key} updated to {value}")

# --- Verification Test ---
if __name__ == "__main__":
    conf = INGRVMConfig()
    
    print("\n--- Configuration Audit ---")
    print(f"P2P Port: {conf.get('node', 'p2p_port')}")
    print(f"Brain Beta: {conf.get('brain', 'beta')}")
    print(f"Spike Cost: {conf.get('economy', 'spike_cost_joules')} J")
    
    # Simulate a user change
    conf.settings['node']['p2p_port'] = 9999
    conf.save()
    print("\n[TEST] Updated port to 9999 and saved.")
    
    # Reload to verify persistence
    new_conf = INGRVMConfig()
    if new_conf.get('node', 'p2p_port') == 9999:
        print("SUCCESS: Configuration persistence verified.")
        
    # Reset for cleanliness
    os.remove("ingrvm_config.json")


