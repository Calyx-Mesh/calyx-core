import os
import sys
import subprocess

class PreFlightCheck:
    """
    Final System Audit before PC Migration.
    Runs every critical logic-test we built tonight.
    """
    def __init__(self):
        self.critical_tests = [
            "ingrvm_0_test.py",
            "test_p2p_node.py",
            "spike_protocol.py",
            "identity_manager.py",
            "ingrvm_packager.py",
            "validator_gate.py",
            "speculative_spike.py",
            "reward_engine.py",
            "blockchain_epoch.py",
            "homeostasis.py",
            "context_memory.py",
            "efficiency_monitor.py",
            "seed_generator.py"
        ]

    def run_all(self):
        print("--- [PROJECT THOR] PRE-FLIGHT INTEGRITY CHECK ---")
        print(f"Auditing {len(self.critical_tests)} logic modules...\n")
        
        passed = 0
        failed = 0
        
        for test in self.critical_tests:
            path = os.path.join("neuromorphic_env", test)
            print(f"[AUDIT] Testing {test:20}...", end="", flush=True)
            
            try:
                # Run the script and hide output unless it fails
                result = subprocess.run(
                    [sys.executable, path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print("✅ PASS")
                    passed += 1
                else:
                    print("❌ FAIL")
                    print(f"--- ERROR IN {test} ---\n{result.stderr}")
                    failed += 1
            except Exception as e:
                print(f"❌ ERROR: {e}")
                failed += 1

        print("\n--- FINAL REPORT ---")
        print(f"Modules Verified: {passed}/{len(self.critical_tests)}")
        if failed == 0:
            print("\nMISSION READY: System is 100% stable for PC Migration.")
        else:
            print(f"\nCRITICAL: {failed} modules failed the audit. Do not migrate yet.")

if __name__ == "__main__":
    audit = PreFlightCheck()
    audit.run_all()
