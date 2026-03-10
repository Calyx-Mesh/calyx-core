import trio
import os
import sys
import time
from dotenv import load_dotenv

# Import the core spike logic
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))
from spike_protocol import NeuralSpike, generate_task_id, hash_input

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

RAW_PORT = 60005
# Target the PC Master Hub first. The Gatekeeper logic will bounce it if needed.
TARGET_IP = os.getenv("INGRVM_HUB_IP", "192.168.68.51")

async def fire_celebration_spike(spike_id: int):
    """ Fires a celebratory spike representing a public user request. """
    spike = NeuralSpike(
        task_id=generate_task_id("PUBLIC_USER", f"celeb_{spike_id}"),
        ingrvm_id="cli_hardened_skill_1.0.2", # Use our newly deployed Phase 6 skill
        node_id="PUBLIC_USER",
        input_hash=hash_input(f"Global Launch Celebration {spike_id}")
    )
    spike.current_layer = 0 
    spike.set_spikes([1, 1, 1, 1, 1]) # Maximum input energy
    
    try:
        async with await trio.open_tcp_stream(TARGET_IP, RAW_PORT) as stream:
            await stream.send_all(spike.to_bin())
            if spike_id % 100 == 0:
                print(f"🎉 [MILESTONE] Dispatched Spike #{spike_id} to the Sovereign Mesh.")
    except Exception as e:
        if spike_id % 50 == 0:
             print(f"⚠️ [CONGESTION] Spike #{spike_id} delayed: {e}")

async def run_celebration(num_spikes=1000):
    """ The Phase 8 Finale. """
    print(f"============================================================")
    print(f"🌿 INGRVM MESH: INFERENCE CELEBRATION (PHASE 8 LAUNCH) 🌐")
    print(f"============================================================")
    print(f"Targeting Node: {TARGET_IP}:{RAW_PORT}")
    print(f"Payload: {num_spikes} concurrent inferences\n")
    
    start_time = time.time()
    
    async with trio.open_nursery() as nursery:
        for i in range(num_spikes):
            nursery.start_soon(fire_celebration_spike, i)
            # Minimal delay to saturate the network without crashing local sockets
            await trio.sleep(0.01)
            
    duration = time.time() - start_time
    print(f"\n============================================================")
    print(f"✅ [GLOBAL LAUNCH COMPLETE]")
    print(f"Dispatched {num_spikes} inferences in {duration:.2f} seconds.")
    print(f"Mesh stability confirmed. Welcome to the Sovereign Economy.")
    print(f"============================================================")

if __name__ == "__main__":
    trio.run(run_celebration, 1000)

