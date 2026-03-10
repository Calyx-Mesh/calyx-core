import trio
import time
from identity_manager import NodeIdentity
from spike_protocol import NeuralSpike, generate_task_id, hash_input, send_spike_raw

from config import INGRVMConfig

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

# LAN Config
conf = INGRVMConfig()
TARGET_IP = conf.get("node", "hub_ip") or "127.0.0.1"
PORT = 60005 # Direct Socket for max speed

async def fire_neural_storm(spikes_per_sec: int = 100, duration_sec: int = 5):
    """
    Stress-tests the PC node by firing a high-frequency burst of signed spikes.
    """
    identity = NodeIdentity()
    node_id = identity.get_public_key_b64()
    
    total_spikes = spikes_per_sec * duration_sec
    delay = 1.0 / spikes_per_sec
    
    print_f(f"--- Launching Neural Storm ({spikes_per_sec} spikes/sec) ---")
    print_f(f"Target: {TARGET_IP}:{PORT} | Total: {total_spikes} spikes")
    
    success_count = 0
    start_time = trio.current_time()
    
    for i in range(total_spikes):
        # 1. Generate & Sign Spike
        spike = NeuralSpike(
            task_id=generate_task_id(node_id, "stress_test"),
            ingrvm_id="ingrvm_0",
            node_id=node_id,
            input_hash=hash_input(f"Probe-{i}")
        )
        spike.set_spikes([1, 1, 1])
        spike.signature = identity.sign_data(spike.to_bin())
        
        # 2. Dispatch via Direct Socket (Fastest path)
        if await send_spike_raw(spike, TARGET_IP, PORT):
            success_count += 1
            
        if i % (spikes_per_sec) == 0 and i > 0:
            print_f(f"[PROBE] {i} spikes dispatched...")
            
        await trio.sleep(delay)

    end_time = trio.current_time()
    elapsed = end_time - start_time
    
    print_f(f"\n--- Storm Concluded ---")
    print_f(f"Elapsed Time: {elapsed:.2f}s")
    print_f(f"Throughput: {success_count / elapsed:.2f} successful spikes/sec")
    
    if success_count > (total_spikes * 0.8):
        print_f("SUCCESS: LAN path sustained high throughput.")
    else:
        print_f("WARNING: High packet loss detected. Check LAN stability.")

if __name__ == "__main__":
    # Start with a moderate test
    try:
        trio.run(fire_neural_storm, 50, 2)
    except Exception as e:
        print_f(f"Probe Error: {e}")
