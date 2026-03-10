import os
import sys
import json
from cryptography.hazmat.primitives.asymmetric import ed25519

def INGRVM_init():
    """
    Scaffolds a fresh INGRVM Node environment.
    Initializes keys, databases, and folder structure.
    """
    print("--- 🌿 INGRVM ENVIRONMENT INITIALIZER ---")
    
    # 1. Folders
    dirs = ["ingrvms", "packages", "logs", "mesh_discovery"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"  [+] Created directory: {d}")

    # 2. Identity Key
    key_path = "identity.key"
    if not os.path.exists(key_path):
        private_key = ed25519.Ed25519PrivateKey.generate()
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes_raw())
        print(f"  [+] Generated new Identity Key: {key_path}")
    else:
        print(f"  [-] Identity Key already exists. Skipping.")

    # 3. Peer Database
    db_path = "peer_db.json"
    if not os.path.exists(db_path):
        with open(db_path, "w") as f:
            json.dump({}, f)
        print(f"  [+] Initialized Peer Database: {db_path}")

    # 4. Config
    config_path = "ingrvm_config.json"
    if not os.path.exists(config_path):
        default_config = {
            "node": {"p2p_port": 60001, "name": "New_INGRVM_Node"},
            "economy": {"max_energy_joules": 1000, "solar_recovery_rate": 5.0}
        }
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"  [+] Created default config: {config_path}")

    print("\nSUCCESS: INGRVM environment is mission-ready.")

if __name__ == "__main__":
    INGRVM_init()

