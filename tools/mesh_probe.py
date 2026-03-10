import socket
import sys
import time
import json

PROBE_PORT = 60006 # Low energy UDP port
HUB_IP = "192.168.68.51"

def send_probe(target_ip, node_id, action=None):
    """
    Sends a low-energy UDP beacon to announce readiness or trigger actions.
    """
    print(f"--- 📡 INGRVM Mesh Probe: {target_ip} ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    payload = {
        "type": "PROBE_READY",
        "node_id": node_id,
        "timestamp": time.time(),
        "action": action
    }
    
    try:
        # Broadcast probe
        sock.sendto(json.dumps(payload).encode(), (target_ip, PROBE_PORT))
        print(f"✅ Probe Beacon dispatched to {target_ip}:{PROBE_PORT}")
    except Exception as e:
        print(f"❌ Probe failed: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    node = sys.argv[1] if len(sys.argv) > 1 else "LAPTOP_RELAY"
    target = sys.argv[2] if len(sys.argv) > 2 else HUB_IP
    action = sys.argv[3] if len(sys.argv) > 3 else None
    send_probe(target, node, action)

