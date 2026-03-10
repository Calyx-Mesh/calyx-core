import sys
import os

# Add Core to path
core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(core_path)

from tools.INGRVM_doctor import run_diagnostics

def run_preflight():
    """
    Final Audit: Unified check of all INGRVM modules for Phase 3.
    """
    print("🌿 --- INGRVM PREFLIGHT MISSION AUDIT v3.0 ---")
    results = []
    
    # 1. Environment Doctor
    print("\n[1] Running System Doctor...")
    try:
        run_diagnostics()
        doctor_passed = True
    except Exception as e:
        print(f"Doctor failed: {e}")
        doctor_passed = False

    # 2. Logic Audit: 1-bit Neural Engines
    print("\n[2] Auditing Neural Engines...")
    try:
        import torch
        from quantization import NeuromorphicQuantizer
        # Test 1-bit packing
        mock = torch.sign(torch.randn(100))
        packed = NeuromorphicQuantizer.bit_pack(mock)
        logic_ok = packed.numel() > 0
        
        # Test Inference Engine
        from ingrvms.sentiment_alpha import SentimentAlpha
        engine = SentimentAlpha()
        res = engine.infer("Audit Test")
        engine_ok = "sentiment" in res
    except Exception as e:
        print(f"Neural Audit failed: {e}")
        logic_ok = False
        engine_ok = False
    
    results.append(("Industrial_Logic", logic_ok))
    results.append(("Neural_Engine", engine_ok))

    # 3. Path Audit
    print("\n[3] Auditing Folders...")
    critical_dirs = [
        os.path.join(core_path, "ingrvms"),
        os.path.join(core_path, "packages"),
        os.path.abspath(os.path.join(core_path, "..", "..", "logs"))
    ]
    all_dirs_ok = True
    for d in critical_dirs:
        if not os.path.exists(d):
            print(f"  [!] Missing: {d}")
            all_dirs_ok = False
    results.append(("Folder_Audit", all_dirs_ok))

    # Summary
    print("\n--- PHASE 3 PREFLIGHT SUMMARY ---")
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        icon = "✅" if passed else "❌"
        # On laptop, we expect Neural logic to fail if no GPU but CPU fallback might work
        print(f"  {icon} {name:15}: {status}")
        if not passed: all_passed = False

    if all_passed:
        print("\n🚀 [ALL SYSTEMS GO] INGRVM Node is mission-ready for Phase 4.")
    else:
        print("\n⚠️ [LOCAL NOTICE] Preflight failed. Expected if running on non-GPU node (Laptop).")

if __name__ == "__main__":
    run_preflight()

