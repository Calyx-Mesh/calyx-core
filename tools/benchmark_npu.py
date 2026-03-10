import torch
import time
import sys
import os
from pathlib import Path

# Add project paths for imports
core_dir = Path(__file__).parent.parent
sys.path.append(str(core_dir))
sys.path.append(str(core_dir.parent / "Mobile"))

from brain_models import MiniBrain
from pytorch_mobile_bridge import INGRVMMobileBridge

def run_npu_benchmark(iterations=500):
    """
    Benchmarks standard vs. Mobile-Optimized inference on the laptop.
    Simulates the speedup expected on Pixel 8 NPU.
    """
    bridge = INGRVMMobileBridge()
    device = torch.device("cpu") # Force CPU to simulate mobile ARM bottlenecks
    
    print(f"--- INGRVM NPU Benchmark: Phase 9 Optimization ---")
    print(f"Device: {device}")
    print(f"Iterations: {iterations}")
    
    # 1. Setup Standard Model
    std_model = MiniBrain(layer_start=0, layer_end=5).to(device)
    std_model.eval()
    
    # 2. Setup Optimized Model (using the bridge)
    # We script the model to allow mobile optimization
    print("\n[STEP] Optimizing model for NPU simulation...")
    try:
        scripted_model = torch.jit.script(std_model)
        from torch.utils.mobile_optimizer import optimize_for_mobile
        opt_model = optimize_for_mobile(scripted_model)
        has_opt = True
    except Exception as e:
        print(f"⚠️ Optimization failed: {e}")
        opt_model = std_model
        has_opt = False

    sample_input = torch.randn(1, 3).to(device)
    
    # --- Benchmark Standard ---
    print(f"\n[1/2] Benchmarking Standard Torch...")
    # Warmup
    for _ in range(10): _ = std_model(sample_input, 0)
    
    start_std = time.time()
    for _ in range(iterations):
        _ = std_model(sample_input, 0)
    end_std = time.time()
    std_time = end_std - start_std
    
    # --- Benchmark Optimized ---
    print(f"[2/2] Benchmarking Mobile-Optimized (QNNPACK)...")
    # Warmup
    for _ in range(10): _ = opt_model(sample_input, 0)
    
    start_opt = time.time()
    for _ in range(iterations):
        _ = opt_model(sample_input, 0)
    end_opt = time.time()
    opt_time = end_opt - start_opt
    
    # --- Results ---
    std_latency = (std_time / iterations) * 1000
    opt_latency = (opt_time / iterations) * 1000
    improvement = ((std_latency - opt_latency) / std_latency) * 1000 if std_latency > 0 else 0
    # Actually improvement is just percentage
    improvement_pct = ((std_latency - opt_latency) / std_latency) * 100 if std_latency > 0 else 0

    print(f"\n[RESULTS]:")
    print(f"Standard Latency:  {std_latency:.3f} ms")
    print(f"Optimized Latency: {opt_latency:.3f} ms")
    
    if has_opt:
        print(f"Performance Gain:  {improvement_pct:.1f}% faster")
    else:
        print("Performance Gain:  N/A (Optimization skipped)")

    if improvement_pct > 5:
        print("\n✅ SUCCESS: Mobile-First SDK provides measurable speedup even on x86.")
    else:
        print("\n⚠️ NOTE: Speedup may only be visible on actual ARM64 NPU hardware.")

if __name__ == "__main__":
    run_npu_benchmark()

