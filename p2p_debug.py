import trio
import torch
import torch.nn as nn
from collections import OrderedDict
from libp2p import new_host
from libp2p.pubsub.pubsub import Pubsub
from libp2p.pubsub.floodsub import FloodSub
from libp2p.security.insecure.transport import InsecureTransport
from multiaddr import Multiaddr
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import PeerInfo
from libp2p.tools.async_service import background_trio_service
from spike_protocol import NeuralSpike, generate_task_id, hash_input
from libp2p.crypto.ed25519 import create_new_key_pair
import os
import logging
import sys
import requests
import json
from dotenv import load_dotenv

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

# Import discovery tool
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
from lan_discovery import discover_hub

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
print_f(f"DEBUG: Loading .env from {env_path}")
load_dotenv(env_path)

print_f(f"DEBUG: INGRVM_BOOTSTRAP_PEERS={os.getenv('INGRVM_BOOTSTRAP_PEERS')}")

PLAINTEXT_PROTOCOL_ID = "/plaintext/2.0.0"
TOPIC_ID = "ingrvm/ingrvm/0"

def make_insecure_host(listen_addrs):
    key_pair = create_new_key_pair()
    insecure_opt = {PLAINTEXT_PROTOCOL_ID: InsecureTransport(key_pair)}
    return new_host(
        key_pair=key_pair,
        listen_addrs=listen_addrs,
        sec_opt=insecure_opt
    )

async def check_hub_connectivity():
    """ Pings the Hub API to verify connectivity. """
    hub_url = os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")
    print_f(f"📡 Checking Hub Connectivity: {hub_url}/api/mesh/ping")
    try:
        # Use a short timeout for the ping
        resp = requests.get(f"{hub_url}/api/mesh/ping", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            print_f(f"✅ Hub Responsive: {data['node_id']} at {data['timestamp']}")
            return True
    except Exception as e:
        print_f(f"❌ Hub Unreachable: {e}")
    return False

async def run_node_a():
    """ The Receiver (Server) - Runs on PC """
    default_ip = socket.gethostbyname(socket.gethostname())
    local_ip = os.getenv("INGRVM_NODE_IP", default_ip)
    p2p_port = int(os.getenv("INGRVM_P2P_PORT", 60001))
    
    print_f(f"[NODE A] Initializing on {local_ip}:{p2p_port}")
    
    listen_addr = Multiaddr(f"/ip4/{local_ip}/tcp/{p2p_port}")
    host = make_insecure_host([listen_addr])
    
    router = FloodSub(protocols=['/floodsub/1.0.0'])
    pubsub = Pubsub(host, router)
    
    async with host.run(listen_addrs=[listen_addr]), background_trio_service(pubsub):
        full_addr = f"/ip4/{local_ip}/tcp/{p2p_port}/p2p/{host.get_id().to_string()}"
        print_f(f"\n--- [NODE A ONLINE] ---")
        print_f(f"Address: {full_addr}")
        print_f("READY. Awaiting spikes...")
        
        sub = await pubsub.subscribe(TOPIC_ID)
        while True:
            message = await sub.get()
            try:
                spike = NeuralSpike.from_bin(message.data)
                if spike.node_id == "PC_MASTER": continue 
                
                print_f(f"\n[RECEIVE] Spike from {spike.node_id} (Task: {spike.task_id})")
                
                ack = NeuralSpike(
                    task_id=spike.task_id,
                    ingrvm_id=spike.ingrvm_id,
                    node_id="PC_MASTER",
                    input_hash=spike.input_hash
                )
                ack.set_spikes([1])
                await pubsub.publish(TOPIC_ID, ack.to_bin())
                print_f(f"[SEND] ACK sent for Task {spike.task_id}")
            except Exception as e:
                print_f(f"[ERROR] {e}")

async def run_node_b():
    """ The Initiator (Client) - Runs on Laptop """
    # 1. Hub Discovery
    hub_ip, hub_port = discover_hub(timeout=10)
    if not hub_ip:
        print_f("❌ Hub Discovery Failed. Reverting to .env defaults.")
        hub_url = os.getenv("INGRVM_HUB_URL")
    else:
        hub_url = f"http://{hub_ip}:{hub_port}"
        print_f(f"🚀 Discovered Hub at {hub_url}")

    # 2. Connectivity Check
    if not await check_hub_connectivity():
        print_f("⚠️ WARNING: API Ping failed. libp2p may also fail.")

    # 3. Get Bootstrap Multiaddr
    # We can fetch this from the Hub API if we implement an endpoint, 
    # but for now we'll assume it's correctly set in .env or known.
    # TODO: Implement /api/mesh/address to get real multiaddr from PC
    addr_str = os.getenv("INGRVM_BOOTSTRAP_PEERS").split(",")[0]
    if "PLACEHOLDER" in addr_str:
         print_f("⚠️ INGRVM_BOOTSTRAP_PEERS contains placeholder. Update .env with real PC Peer ID!")

    maddr = Multiaddr(addr_str)
    peer_id_str = maddr.value_for_protocol(0x1a5)
    peer_id = PeerID.from_string(peer_id_str)
    
    # Extract IP and Port from the multiaddr
    target_ip = maddr.value_for_protocol(0x04) # ip4
    target_port = maddr.value_for_protocol(0x06) # tcp
    
    target_multiaddr = Multiaddr(f"/ip4/{target_ip}/tcp/{target_port}")
    peer_info = PeerInfo(peer_id, [target_multiaddr])
    
    client_listen = Multiaddr("/ip4/0.0.0.0/tcp/0")
    host = make_insecure_host([client_listen])
    router = FloodSub(protocols=['/floodsub/1.0.0'])
    pubsub = Pubsub(host, router)
    
    async with host.run(listen_addrs=[]), background_trio_service(pubsub):
        print_f(f"[NODE B] Connecting to PC: {target_ip}:{target_port}...")
        try:
            await host.connect(peer_info)
            print_f("[NODE B] SUCCESS: Connected to PC!")
        except Exception as e:
            print_f(f"❌ Connection Failed: {e}")
            return
        
        sub = await pubsub.subscribe(TOPIC_ID)
        await trio.sleep(1) # Wait for pubsub propagation
        
        spike = NeuralSpike(
            task_id=generate_task_id("LAPTOP_RELAY", "ingrvm_0"),
            ingrvm_id="ingrvm_0",
            node_id="LAPTOP_RELAY",
            input_hash=hash_input("Phase 5 P2P Test")
        )
        spike.set_spikes([1, 1, 1])
        
        print_f(f"\n[SEND] Publishing Spike (Task: {spike.task_id})")
        await pubsub.publish(TOPIC_ID, spike.to_bin())
        
        print_f("[WAIT] Awaiting ACK from PC...")
        with trio.fail_after(15):
            while True:
                message = await sub.get()
                resp = NeuralSpike.from_bin(message.data)
                if resp.node_id == "PC_MASTER":
                    print_f(f"\n[SUCCESS] ACK Received from PC!")
                    return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python p2p_debug.py <a|b>")
    elif sys.argv[1].lower() == 'a':
        trio.run(run_node_a)
    elif sys.argv[1].lower() == 'b':
        trio.run(run_node_b)

