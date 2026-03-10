import socket
import sys
import os
from spike_protocol import NeuralSpike, generate_task_id, hash_input

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

LAN_IP = "192.168.68.52"
PORT = 60005 # Using a fresh port

def run_server():
    """ Runs on PC: Receives raw binary spikes. """
    print_f(f"--- [PC] INGRVM Direct Socket Server ---")
    print_f(f"Listening on {LAN_IP}:{PORT}...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LAN_IP, PORT))
        s.listen()
        
        while True:
            conn, addr = s.accept()
            with conn:
                print_f(f"\n[RECEIVE] Connection from {addr}")
                data = conn.recv(4096)
                if not data: break
                
                try:
                    spike = NeuralSpike.from_bin(data)
                    print_f(f"[SUCCESS] Spike Received! Task: {spike.task_id}")
                    print_f(f"[DATA] Indices: {spike.sparse_indices}")
                    
                    # Send Ack
                    conn.sendall(b"ACK_RECEIVED")
                except Exception as e:
                    print_f(f"[ERROR] Decoding failure: {e}")

def run_client():
    """ Runs on Laptop: Sends a raw binary spike. """
    print_f(f"--- [LAPTOP] INGRVM Direct Socket Client ---")
    print_f(f"Connecting to PC at {LAN_IP}:{PORT}...")
    
    # Create a real NeuralSpike
    spike = NeuralSpike(
        task_id=generate_task_id("LAPTOP_PROBE", "lan_test"),
        ingrvm_id="ingrvm_0",
        node_id="LAPTOP_PROBE",
        input_hash=hash_input("Raw Socket Test")
    )
    spike.set_spikes([1, 0, 1])
    payload = spike.to_bin()
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((LAN_IP, PORT))
            print_f(f"[SEND] Dispatching Spike Binary ({len(payload)} bytes)...")
            s.sendall(payload)
            
            response = s.recv(1024)
            print_f(f"[SUCCESS] Server Response: {response.decode()}")
    except Exception as e:
        print_f(f"[FAILURE] Could not reach PC: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lan_relay.py <server|client>")
    elif sys.argv[1].lower() == "server":
        run_server()
    elif sys.argv[1].lower() == "client":
        run_client()
