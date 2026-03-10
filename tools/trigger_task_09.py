import sys
import os
import trio
import time

# Add parent to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spike_protocol import NeuralSpike, send_spike_raw

HUB_IP = "127.0.0.1" 
PORT = 60005

async def trigger_async():
    """ Sends a real inference spike to start Task #09 using async trio socket. """
    print("--- 🧠 Triggering Task #09: Multi-Hop Inference (Async) ---")
    
    spike = NeuralSpike(
        task_id=f"TASK_09_{int(time.time())}",
        ingrvm_id="INGRVM-1.0",
        node_id="TRIGGER_TOOL",
        current_layer=6,
        model_name="Llama-3-8B-BitNet",
        input_hash="0xDEADBEEF",
        ttl=50
    )
    spike.set_spikes([1, 0, 1])
    
    print(f"Firing initial sparse spike to {HUB_IP}:{PORT}...")
    success = await send_spike_raw(spike, HUB_IP, PORT)
    
    if success:
        print("✅ Spike injected into mesh.")
    else:
        print("❌ Failed to inject spike.")

if __name__ == "__main__":
    trio.run(trigger_async)
