import subprocess
import time
import sys
import os

class PhoenixSupervisor:
    """
    The Watchdog of the INGRVM Mesh.
    Monitors the Neural Node process. If it crashes, it rises from the ashes.
    """
    def __init__(self, target_script: str = "neural_node.py"):
        self.target_script = target_script
        self.restart_count = 0
        self.max_restarts = 5
        self.last_crash_time = time.time()

    def rise(self):
        print(f"--- [PHOENIX] Supervisor Active. Watching: {self.target_script} ---")
        
        while True:
            # Launch the node
            print(f"[PHOENIX] Spawning process (Attempt #{self.restart_count + 1})...")
            
            # Using same python executable
            process = subprocess.Popen(
                [sys.executable, self.target_script],
                stdout=sys.stdout, # Pipe output to console
                stderr=sys.stderr
            )
            
            # Wait for it to finish (or crash)
            exit_code = process.wait()
            
            # Analysis
            if exit_code == 0:
                print("[PHOENIX] Process exited cleanly (Manual Stop). Supervisor shutting down.")
                break
            else:
                print(f"\n[PHOENIX] CRITICAL: Node crashed with Exit Code {exit_code}")
                self.handle_crash()

    def handle_crash(self):
        now = time.time()
        # Reset counter if stable for > 10 seconds
        if now - self.last_crash_time > 10:
            self.restart_count = 0
            
        self.restart_count += 1
        self.last_crash_time = now
        
        if self.restart_count > self.max_restarts:
            print("[PHOENIX] ERROR: Restart loop detected. Giving up to prevent CPU burn.")
            sys.exit(1)
            
        print(f"[PHOENIX] Resurrecting in 2 seconds...")
        time.sleep(2)

# --- Verification Test ---
if __name__ == "__main__":
    # Create a dummy script that crashes on purpose
    dummy_path = "dummy_crash.py"
    with open(dummy_path, "w") as f:
        f.write("import time; import sys; print('I am alive...'); time.sleep(1); print('I am dying!'); sys.exit(1)")
        
    supervisor = PhoenixSupervisor(dummy_path)
    supervisor.max_restarts = 2 # Limit for test
    
    try:
        supervisor.rise()
    except SystemExit:
        print("\nSUCCESS: Supervisor detected crash loop and enforced safety limit.")
        
    if os.path.exists(dummy_path):
        os.remove(dummy_path)
