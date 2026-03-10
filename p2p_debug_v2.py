import trio
import os
import sys
import socket
import requests
import json
from dotenv import load_dotenv

# INGRVM Imports
from spike_protocol import NeuralSpike, generate_task_id, hash_input

# Import discovery tool
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
from lan_discovery import discover_hub

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

def print_f(*args, **kwargs):
    print(" ".join(map(str, args)), flush=True)

RAW_PORT = 60005 # Direct LAN fallback

async def run_server():
    """ Node A (PC) - Listens for raw spikes. """
    local_ip = os.getenv("INGRVM_NODE_IP", socket.gethostbyname(socket.gethostname()))
    print_f(f"--- [RAW SOCKET SERVER] ---")
    print_f(f"Node: PC_MASTER | IP: {local_ip}:{RAW_PORT}")
    
    async def handler(stream):
        peer = stream.socket.getpeername()
        print_f(f"\n[RECEIVE] Connection from {peer}")
        try:
            data = await stream.receive_some(16384)
            if data:
                spike = NeuralSpike.from_bin(data)
                print_f(f"[SPIKE] Task: {spike.task_id[:8]} | From: {spike.node_id} | Layers: {spike.current_layer}")
                
                # Send ACK back
                ack = NeuralSpike(
                    task_id=spike.task_id,
                    ingrvm_id=spike.ingrvm_id,
                    node_id="PC_MASTER",
                    input_hash=spike.input_hash
                )
                ack.set_spikes([1])
                await stream.send_all(ack.to_bin())
                print_f(f"[SEND] ACK sent to {peer}")
        except Exception as e:
            print_f(f"❌ Server Error: {e}")

    await trio.serve_tcp(handler, RAW_PORT, host="0.0.0.0")

async def run_client():
    """ Node B (Laptop) - Sends a spike to discovered PC. """
    print_f("--- [RAW SOCKET CLIENT] ---")
    
    # 1. Discover Hub
    hub_ip, hub_port = discover_hub(timeout=5)
    if not hub_ip:
        hub_ip = os.getenv("INGRVM_BOOTSTRAP_PEERS", "").split("/")[2] if "/" in os.getenv("INGRVM_BOOTSTRAP_PEERS", "") else "192.168.68.51"
        print_f(f"⚠️ Discovery failed. Using fallback IP: {hub_ip}")
    else:
        print_f(f"🚀 Discovered PC at {hub_ip}")

    # 2. Create Spike
    spike = NeuralSpike(
        task_id=generate_task_id("LAPTOP_RELAY", "ingrvm_0"),
        ingrvm_id="ingrvm_0",
        node_id="LAPTOP_RELAY",
        input_hash=hash_input("Raw Socket Test")
    )
    spike.set_spikes([1, 0, 1])
    
    # 3. Connect and Send
    print_f(f"[SEND] Connecting to {hub_ip}:{RAW_PORT}...")
    try:
        async with await trio.open_tcp_stream(hub_ip, RAW_PORT) as stream:
            await stream.send_all(spike.to_bin())
            print_f(f"[SEND] Spike fired. Awaiting ACK...")
            
            # Wait for response
            with trio.fail_after(5):
                resp_data = await stream.receive_some(16384)
                if resp_data:
                    ack = NeuralSpike.from_bin(resp_data)
                    if ack.node_id == "PC_MASTER":
                        print_f(f"✅ SUCCESS: ACK received from PC Master!")
    except Exception as e:
        print_f(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python p2p_debug_v2.py <server|client>")
    elif sys.argv[1] == "server":
        trio.run(run_server)
    elif sys.argv[1] == "client":
        trio.run(run_client)

