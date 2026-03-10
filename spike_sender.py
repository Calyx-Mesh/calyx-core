import trio
import os
import json
import sys
import time
from libp2p import new_host
from libp2p.pubsub.pubsub import Pubsub
from libp2p.pubsub.floodsub import FloodSub
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import PeerInfo
from multiaddr import Multiaddr
from libp2p.tools.async_service import background_trio_service

from shard_manager import ShardManager
from spike_protocol import NeuralSpike, generate_task_id, hash_input, send_spike_raw

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

TOPIC_ID = "ingrvm/ingrvm/0"
DISCOVERY_TOPIC = "ingrvm/mesh/discovery"
ADDR_FILE = "neuromorphic_env/current_node_addr.txt"
RAW_PORT = 60005
LAN_IP = "127.0.0.1"

async def process_response(spike_bin, node_id, nursery):
    try:
        spike = NeuralSpike.from_bin(spike_bin)
        # Accept if it's from someone else OR if it's our spike that has been forwarded/processed
        if spike.node_id != node_id or spike.current_layer > 5:
            print_f(f"\n[SUCCESS] Pipeline Loopback Received!")
            print_f(f"[ROUTING] Task {spike.task_id} is now at Layer {spike.current_layer}")
            
            # Extract prediction from spikes
            results = spike.get_spikes()
            if results:
                prediction = "Positive" if results[0] == 1 else "Negative"
                print_f(f"[BRAIN] Mesh Prediction: {prediction} (Result: {results[0]})")
            
            nursery.cancel_scope.cancel()
            return True
    except Exception as e:
        print_f(f"[ERROR] process_response: {e}")
    return False

async def response_loop(sub, nursery, node_id, shard_mgr, spike_recv_ch):
    """ Listens for responses via P2P AND File-Mesh. """
    async with trio.open_nursery() as sub_nursery:
        async def p2p_listener():
            while True:
                msg = await sub.get()
                if await process_response(msg.data, node_id, nursery):
                    return

        async def file_listener():
            async for spike_bin in spike_recv_ch:
                if await process_response(spike_bin, node_id, nursery):
                    return

        sub_nursery.start_soon(p2p_listener)
        sub_nursery.start_soon(file_listener)

async def discovery_listener(sub, shard_mgr):
    while True:
        message = await sub.get()
        await shard_mgr.handle_discovery_message(message)

async def wait_for_pc_ready(shard_mgr, target_node_id):
    """
    Solarpunk Handshake: Wait for the PC's discovery file to appear 
    and be recently updated.
    """
    print_f(f"[SENDER] Waiting for PC Node ({target_node_id[:8]}) to signal READY...")
    
    while True:
        await shard_mgr.poll_mesh_files_once()
        if target_node_id in shard_mgr.mesh_shards:
            print_f("[SENDER] PC Node found in Mesh Shards. Synchronization verified.")
            return
        await trio.sleep(2)

async def send_spike():
    print_f("Waiting for node address...")
    while not os.path.exists(ADDR_FILE):
        await trio.sleep(0.5)
    
    with open(ADDR_FILE, "r") as f:
        target_full_addr = f.read().strip()
    
    parts = target_full_addr.split("/p2p/")
    target_multiaddr_str = parts[0]
    peer_id_str = parts[1]
    
    host = new_host()
    node_id = "SENDER_PROBE"
    
    # Sender hosts layers 6-10
    shard_mgr = ShardManager(node_id)
    shard_mgr.register_shard("INGRVM-1.0", 6, 10, 0.5)
    
    # File-Mesh channel
    spike_send_ch, spike_recv_ch = trio.open_memory_channel(10)
    shard_mgr.file_spike_queue = spike_send_ch
    
    router_impl = FloodSub(protocols=['/floodsub/1.0.0'])
    pubsub = Pubsub(host, router_impl)
    
    async with host.run(listen_addrs=[]), background_trio_service(pubsub), trio.open_nursery() as nursery:
        print_f(f"[SENDER] Host started. ID: {host.get_id().to_string()[:8]}")
        
        # Start File-Mesh Polling
        nursery.start_soon(shard_mgr.poll_mesh_files)
        
        # Monkey-patch poll_mesh_files_once for the handshake
        async def poll_once():
            for filename in os.listdir(shard_mgr.discovery_dir):
                if filename.endswith(".json") and not filename.startswith(shard_mgr.node_id):
                    try:
                        with open(os.path.join(shard_mgr.discovery_dir, filename), "r") as f:
                            data = json.load(f)
                            sid = data["node_id"]
                            from shard_manager import ModelShard
                            shards = [ModelShard(**s) for s in data["shards"]]
                            shard_mgr.mesh_shards[sid] = shards
                    except Exception: pass
        shard_mgr.poll_mesh_files_once = poll_once

        await wait_for_pc_ready(shard_mgr, peer_id_str)
        
        # P2P connection logic
        try:
            with trio.fail_after(10):
                peer_id = PeerID.from_string(peer_id_str)
                target_multiaddr = Multiaddr(target_multiaddr_str)
                await host.connect(PeerInfo(peer_id, [target_multiaddr]))
                print_f(f"[SENDER] P2P CONNECTED.")
        except Exception:
            print_f(f"[SENDER] P2P Handshake failed. Using Robust Fallbacks.")
        
        sub = await pubsub.subscribe(TOPIC_ID)
        discovery_sub = await pubsub.subscribe(DISCOVERY_TOPIC)
        
        nursery.start_soon(response_loop, sub, nursery, node_id, shard_mgr, spike_recv_ch)
        nursery.start_soon(discovery_listener, discovery_sub, shard_mgr)
        
        # --- Dispatch ---
        spike = NeuralSpike(
            task_id=generate_task_id(node_id, "ingrvm_0"),
            ingrvm_id="ingrvm_0_sentiment_trained",
            node_id=node_id,
            input_hash=hash_input("Multi-Hop Handshake"),
            current_layer=5 
        )
        spike.set_spikes([1, 1, 1])
        
        print_f(f"[SENDER] Initiating Spike at Layer {spike.current_layer}...")
        
        # Try P2P, then Raw Socket, then File Mesh
        sent = False
        if host.get_network().get_connections():
            try:
                await pubsub.publish(TOPIC_ID, spike.to_bin())
                print_f("[SENDER] Dispatched via P2P")
                sent = True
            except Exception: pass
            
        if not sent:
            if await send_spike_raw(spike, LAN_IP, RAW_PORT):
                print_f("[SENDER] Dispatched via Raw Socket")
                sent = True
                
        if not sent:
            shard_mgr.send_file_spike(peer_id_str, spike.to_bin())
            print_f("[SENDER] Dispatched via File Mesh")
            sent = True

        print_f("[SENDER] Waiting for response (60s timeout)...")
        with trio.fail_after(60):
            await trio.sleep_forever()

if __name__ == "__main__":
    import traceback
    try:
        trio.run(send_spike)
    except trio.Cancelled:
        pass
    except Exception as e:
        traceback.print_exc()
        print_f(f"Sender Error: {e}")
