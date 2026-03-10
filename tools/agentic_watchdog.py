import os
import time
import json
import subprocess
import sys

# Add Core to path for CortexBus
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class AgenticWatchdog:
    """
    Phase 10: The Headless Trigger.
    Monitors the Mailroom for new task files and triggers the Agentic Swarm.
    Replaces manual 'Rule 0' polling with event-driven execution.
    """
    def __init__(self, watch_dir, poll_interval=5):
        self.watch_dir = watch_dir
        self.poll_interval = poll_interval
        self.seen_files = set()
        self._initialize_seen()

    def _initialize_seen(self):
        """ Mark existing files as seen so we only trigger on NEW ones. """
        if not os.path.exists(self.watch_dir):
            os.makedirs(self.watch_dir, exist_ok=True)
        for f in os.listdir(self.watch_dir):
            if f.endswith(".md"):
                self.seen_files.add(f)
        print(f"👁️ Watchdog active on: {self.watch_dir} ({len(self.seen_files)} existing files ignored)")

    def start(self):
        """ Main polling loop. """
        try:
            while True:
                current_files = set([f for f in os.listdir(self.watch_dir) if f.endswith(".md")])
                new_files = current_files - self.seen_files
                
                if new_files:
                    for f in new_files:
                        self._trigger_swarm(f)
                        self.seen_files.add(f)
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down Watchdog...")

    def _trigger_swarm(self, filename):
        """ 
        Task #16 Integration:
        1. Notify the Cortex Bus.
        2. (Future) Trigger Headless Gemini CLI.
        """
        file_path = os.path.join(self.watch_dir, filename)
        print(f"🔔 EVENT DETECTED: {filename} dropped into Mailroom.")
        
        # Log the event
        log_entry = {
            "t": time.time(),
            "event": "WATCHDOG_TRIGGER",
            "file": filename,
            "status": "NOTIFIED"
        }
        print(f"🚀 TRIGGERING SWARM: Processing {filename}...")
        
        # Mocking the Gemini CLI trigger
        # cmd = ["gemini", "--prompt", f"Identify as PC_MASTER. Process the incoming task in {file_path}"]
        # subprocess.Popen(cmd)
        
        # Notify local Cortex Bus if it's running
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 60006))
                msg = json.dumps({
                    "topic": "task_inbox",
                    "payload": {"file": filename, "path": file_path}
                })
                s.sendall(msg.encode())
                print(f"✅ Cortex Bus Notified.")
        except Exception:
            print("⚠️ Cortex Bus not responding. Logging event locally.")

if __name__ == "__main__":
    # Watch the INGRVM Mailroom
    MAILROOM = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Framework", "Mailroom"))
    watchdog = AgenticWatchdog(MAILROOM)
    watchdog.start()

