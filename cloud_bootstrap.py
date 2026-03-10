import json
import os
import sys
import requests
import time
from typing import List, Dict

# INGRVM Imports
from config import INGRVMConfig

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

class CloudBootstrap:
    """
    Phase 8 Task #1: The Cloud Seed Generator.
    Prepares high-uptime 'Lighthouse' nodes for deployment to 
    public cloud environments (DigitalOcean, AWS, etc.).
    """
    def __init__(self):
        self.conf = INGRVMConfig()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.bootstrap_path = os.path.join(base_dir, "bootstrap_list.json")
        self.compose_path = os.path.join(base_dir, "lighthouse-compose.yml")
        
    def generate_seed_config(self, public_ip: str, node_id: str) -> str:
        """
        Generates a Multiaddr for a cloud seed node.
        Format: /ip4/<ip>/tcp/60000/p2p/<node_id>
        """
        addr = f"/ip4/{public_ip}/tcp/60000/p2p/{node_id}"
        print_f(f"[CLOUD] Generated entry point: {addr}")
        return addr

    def update_global_registry(self, new_seeds: List[str]):
        """
        Updates the local bootstrap_list.json with new public seeds.
        """
        if not os.path.exists(self.bootstrap_path):
            current = []
        else:
            with open(self.bootstrap_path, "r") as f:
                current = json.load(f)
        
        updated = list(set(current + new_seeds))
        
        with open(self.bootstrap_path, "w") as f:
            json.dump(updated, f, indent=4)
            
        print_f(f"✅ [CLOUD] {len(new_seeds)} new seeds registered. Total Entry Points: {len(updated)}")

    def generate_docker_stack(self):
        """
        Generates a Docker Compose stack for a Lighthouse node.
        """
        compose_content = """
version: '3.8'
services:
  INGRVM-lighthouse:
    image: INGRVM-mesh/lighthouse:latest
    ports:
      - "60000:60000"
      - "8000:8000"
    environment:
      - INGRVM_NODE_ROLE=LIGHTHOUSE
      - INGRVM_P2P_PORT=60000
    volumes:
      - ./lighthouse_env:/app/neuromorphic_env
    restart: always
"""
        with open(self.compose_path, "w") as f:
            f.write(compose_content)
        print_f(f"✅ [CLOUD] '{os.path.basename(self.compose_path)}' generated for cloud deployment.")

if __name__ == "__main__":
    print_f("--- INGRVM Cloud Bootstrap CLI ---")
    cb = CloudBootstrap()
    
    # Example: Registering the first 2 Austin Seed Nodes (Mock IPs)
    seeds = [
        cb.generate_seed_config("159.203.184.55", "12D3KooW_SEED_AUSTIN_01"),
        cb.generate_seed_config("167.99.12.201", "12D3KooW_SEED_AUSTIN_02")
    ]
    
    cb.update_global_registry(seeds)
    cb.generate_docker_stack()

