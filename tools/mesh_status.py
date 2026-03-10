import requests
import json
import sys
import os
import socket

HUB_IP = "192.168.68.51"
HUB_PORT = 8000
NODE_PORT = 60005

def check_socket(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((ip, port))
            return True
    except Exception:
        return False

def check_status():
    print(f"--- 🏥 INGRVM Mesh Health Check ---")
    
    # 1. Check Hub Connectivity
    try:
        resp = requests.get(f"http://{HUB_IP}:{HUB_PORT}/api/rewards", timeout=2)
        print(f"✅ Hub API: ONLINE ({HUB_IP})")
    except Exception:
        print(f"❌ Hub API: OFFLINE. Cannot verify mesh status.")
        return False

    # 2. Check Discovery Files (Last Seen)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    discovery_dir = os.path.join(base_dir, "mesh_discovery")
    
    if not os.path.exists(discovery_dir):
        print("⚠️ Discovery directory missing.")
        return False

    all_ready = True
    nodes_found = 0
    
    for filename in os.listdir(discovery_dir):
        if filename.endswith(".json"):
            path = os.path.join(discovery_dir, filename)
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    node_id = data.get("node_id", "UNK")
                    # Ignore legacy or probe nodes
                    if len(node_id) > 20 or node_id in ["SENDER_PROBE", "NODE_A"]: continue
                    
                    nodes_found += 1
                    shards = data.get("shards", [])
                    node_ip = shards[0].get("node_ip", "127.0.0.1") if shards else "127.0.0.1"
                    is_ready = all(s.get("is_ready", False) for s in shards)
                    
                    # 3. VERIFY TCP REACHABILITY
                    socket_ok = check_socket(node_ip, NODE_PORT) if node_id != "PC_MASTER" else True
                    
                    status = "READY" if (is_ready and socket_ok) else "OFFLINE/BLOCKED"
                    if not (is_ready and socket_ok): all_ready = False
                    
                    print(f"  - Node {node_id}: {status} ({node_ip})")
                    if not socket_ok and node_id != "PC_MASTER":
                        print(f"    ⚠️ Port {NODE_PORT} unreachable. Check Firewall.")
                except Exception:
                    pass
    
    if nodes_found < 2:
        print("⚠️ Waiting for mesh nodes to register (PC + Laptop required).")
        all_ready = False

    if all_ready:
        print("\n🟢 MESH READY FOR TEST.")
    else:
        print("\n🔴 MESH NOT READY. Coordinate via Mailroom.")
    
    return all_ready

if __name__ == "__main__":
    check_status()

if __name__ == "__main__":
    check_status()

