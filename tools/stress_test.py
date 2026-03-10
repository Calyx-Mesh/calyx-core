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

# Ensure this matches the Laptop Relay's listening port
RAW_PORT = 60005
TARGET_IP = "192.168.68.53" # Laptop JadeEnvy IP based on previous mail

# If we want to dynamically discover, we could use lan_discovery, 
# but hardcoding for a targeted stress test is more reliable.

async def fire_spike(spike_id: int):
    """ Fires a single spike at the Laptop Relay. """
    spike = NeuralSpike(
        task_id=generate_task_id("PC_MASTER", f"stress_{spike_id}"),
        ingrvm_id="sentiment_alpha",
        node_id="PC_MASTER",
        input_hash=hash_input(f"Stress Test Pulse {spike_id}")
    )
    # Simulate a raw input spike starting at Layer 0 (Mobile's domain, but we're testing routing)
    spike.current_layer = 0 
    spike.set_spikes([1, 0, 1, 1, 0])
    
    try:
        async with await trio.open_tcp_stream(TARGET_IP, RAW_PORT) as stream:
            await stream.send_all(spike.to_bin())
            print(f"[SPIKE {spike_id}] Dispatched to {TARGET_IP}:{RAW_PORT}")
            
            # Wait briefly for an ACK or Routing Confirmation
            with trio.fail_after(2):
                resp_data = await stream.receive_some(4096)
                if resp_data:
                    print(f"[SPIKE {spike_id}] ACK received.")
    except trio.TooSlowError:
        print(f"[SPIKE {spike_id}] Timeout - Node busy processing.")
    except Exception as e:
        print(f"[SPIKE {spike_id}] Failed: {e}")

async def run_stress_test(num_spikes=50):
    """ Fires a barrage of spikes to test Nursery and Gatekeeper resilience. """
    print(f"--- [PHASE 5] MESH STRESS TEST INITIATED ---")
    print(f"Targeting Node: {TARGET_IP}:{RAW_PORT}")
    print(f"Payload: {num_spikes} concurrent spikes\n")
    
    start_time = time.time()
    
    async with trio.open_nursery() as nursery:
        for i in range(num_spikes):
            nursery.start_soon(fire_spike, i)
            # Add a tiny delay to prevent local socket exhaustion
            await trio.sleep(0.05)
            
    duration = time.time() - start_time
    print(f"\n--- [TEST COMPLETE] ---")
    print(f"Dispatched {num_spikes} spikes in {duration:.2f} seconds.")
    print(f"Check the Dashboard or Laptop logs to verify successful routing.")

if __name__ == "__main__":
    trio.run(run_stress_test, 100) # Start with 100 spikes
