import trio
import time
from typing import List, Dict
from spike_protocol import NeuralSpike

class PipelineBuffer:
    """
    Queueing system for high-throughput sharding.
    Collects spikes and processes them in batches to reduce P2P overhead.
    """
    def __init__(self, batch_size: int = 8, timeout_ms: int = 100, is_relay: bool = False):
        # Laptop/Relay nodes should use smaller batches and lower latency
        self.batch_size = 2 if is_relay else batch_size
        self.timeout_ms = (20 if is_relay else timeout_ms) / 1000.0
        self.queue: List[NeuralSpike] = []
        self.last_flush = time.time()
        
        if is_relay:
            print(f"[BUFFER] Initialized in LOW-LATENCY RELAY MODE (Batch: {self.batch_size}, Timeout: {self.timeout_ms*1000}ms)")

    async def add_spike(self, spike: NeuralSpike, process_fn):
        """Add a spike to the buffer. Flushes if batch is full or timeout reached."""
        self.queue.append(spike)
        
        if len(self.queue) >= self.batch_size or (time.time() - self.last_flush) > self.timeout_ms:
            await self.flush(process_fn)

    async def flush(self, process_fn):
        """Processes all spikes in the current buffer."""
        if not self.queue:
            return
            
        current_batch = self.queue[:]
        self.queue = []
        self.last_flush = time.time()
        
        print(f"[BUFFER] Flushing batch of {len(current_batch)} spikes...")
        for spike in current_batch:
            await process_fn(spike)

# --- Verification ---
async def test_buffer():
    buffer = PipelineBuffer(batch_size=3, timeout_ms=500)
    
    async def mock_process(spike):
        print(f"Processed: {spike.task_id}")

    spike = NeuralSpike(task_id="T1", ingrvm_id="s", node_id="N", input_hash="h")
    
    print("Adding 2 spikes (Batch size is 3)...")
    await buffer.add_spike(spike, mock_process)
    await buffer.add_spike(spike, mock_process)
    
    print("Waiting for timeout flush...")
    await trio.sleep(1)
    await buffer.add_spike(spike, mock_process) # Should trigger flush

if __name__ == "__main__":
    trio.run(test_buffer)
