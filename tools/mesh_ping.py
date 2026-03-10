import sys
import os
import trio
import time
import json

# Add parent to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spike_protocol import NeuralSpike, send_spike_raw

HUB_IP = "192.168.68.51" # PC Master

async def ping_node(target_ip):
    """ Sends a dummy spike to measure LAN round-trip latency. """
    print(f"--- ⚡ INGRVM Mesh Ping: {target_ip} ---")
    
    spike = NeuralSpike(
        task_id=f"PING_{int(time.time())}",
        ingrvm_id="diag_pulse",
        node_id="DIAG_TOOL",
        input_hash="0x0"
    )
    
    start_time = time.time()
    
    success = await send_spike_raw(spike, target_ip)
    
    if success:
        elapsed = (time.time() - start_time) * 1000
        print(f"✅ Pulse delivered in {elapsed:.2f}ms")
    else:
        print(f"❌ Failed to reach node at {target_ip}")

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else HUB_IP
    try:
        trio.run(ping_node, ip)
    except KeyboardInterrupt:
        pass

