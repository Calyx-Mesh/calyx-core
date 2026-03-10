import torch
import time
import sys
import os

# Add parent dir to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ingrvms.sentiment_alpha import SentimentAlpha
from tools.hardware_monitor import HardwareProtector

def run_benchmark(iterations=1000):
    """
    Benchmarks the 1-bit Sentiment Alpha on the 1080 Ti.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    monitor = HardwareProtector()
    engine = SentimentAlpha()
    
    print(f"--- Sentiment Alpha 1-Bit Benchmark ---")
    print(f"Hardware: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"Iterations: {iterations}")
    
    text = "INGRVM is scaling the Global Brain with 1-bit neuromorphic spikes."
    
    # Warmup
    for _ in range(10):
        _ = engine.infer(text)
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    start_time = time.time()
    
    for _ in range(iterations):
        _ = engine.infer(text)
        
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    total_time = time.time() - start_time
    
    avg_latency = (total_time / iterations) * 1000
    throughput = iterations / total_time
    
    print(f"\n[RESULTS]:")
    print(f"Avg Latency: {avg_latency:.3f} ms")
    print(f"Throughput:  {throughput:.1f} inferences/sec")
    
    vitals = monitor.get_gpu_vitals()
    if vitals:
        print(f"End Temp:    {vitals['temp']}°C")
        print(f"VRAM Used:   {vitals['vram_used']:.0f} MB")

if __name__ == "__main__":
    run_benchmark()

