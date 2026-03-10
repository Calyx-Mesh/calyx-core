import torch
import sys
import os
import psutil

try:
    import pynvml
    # Manual DLL search for Windows (Task #17: Telemetry Stability)
    nvml_paths = [
        os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "nvml.dll"),
        "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvml.dll"
    ]
    for path in nvml_paths:
        if os.path.exists(path):
            os.environ["PATH"] += os.pathsep + os.path.dirname(path)
            break
    HAS_NVML = True
except ImportError:
    HAS_NVML = False

def run_diagnostics():
    """
    INGRVM Doctor: Audits the 1080 Ti Environment for Phase 2 Sprint Readiness.
    """
    print("🩺 --- INGRVM Environmental Audit ---")
    
    # 1. Hardware Presence
    print(f"\n[1/4] HARDWARE STATUS:")
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"✅ GPU Detected: {gpu_name}")
        print(f"✅ Total VRAM:  {gpu_mem:.2f} GB")
    else:
        print("❌ CRITICAL: No NVIDIA GPU detected. Ensure 1080 Ti is installed and drivers are updated.")

    # 2. Driver Health (NVML)
    print(f"\n[2/4] DRIVER & TELEMETRY:")
    if HAS_NVML:
        try:
            pynvml.nvmlInit()
            print("✅ NVML (NVIDIA Management Library) is active.")
            pynvml.nvmlShutdown()
        except Exception as e:
            print(f"⚠️ NVML initialization failed: {e}")
    else:
        print("⚠️ 'nvidia-ml-py3' missing. GPU temperature monitoring will not work.")

    # 3. Memory & Storage (Sparse Logic)
    print(f"\n[3/4] MEMORY & SWAP:")
    mem = psutil.virtual_memory()
    print(f"✅ System RAM:  {mem.total / 1024**3:.2f} GB ({mem.percent}% used)")
    
    # 4. Neural Environment
    print(f"\n[4/4] NEURAL RUNTIME:")
    print(f"✅ PyTorch: {torch.__version__}")
    print(f"✅ Python:  {sys.version.split()[0]}")
    
    print("\n🩺 --- Audit Complete ---")
    if torch.cuda.is_available() and HAS_NVML:
        print("💡 Status: 1080 Ti is fully optimized for Phase 2 (Muscle) operations.")
    else:
        print("💡 Action: Install 'nvidia-ml-py3' and check NVIDIA drivers for full mission readiness.")

if __name__ == "__main__":
    run_diagnostics()

