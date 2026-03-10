import json
import os
import time
from typing import Dict, Any

class INGRVMLogger:
    """
    INGRVM Logger: Rotates logs and provides structured JSON for the Hub's log stream.
    """
    def __init__(self, log_path="logs/node_activity.jsonl", max_lines=1000):
        self.log_path = log_path
        self.max_lines = max_lines
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log(self, event: str, data: Dict[str, Any]):
        """
        Logs a structured event to the JSONL log file.
        """
        log_entry = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "data": data
        }
        
        # 1. Write the new entry
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
        # 2. Rotate if needed
        self.rotate_if_needed()

    def rotate_if_needed(self):
        """
        Ensures the log file doesn't grow indefinitely.
        """
        if not os.path.exists(self.log_path):
            return
            
        with open(self.log_path, 'r') as f:
            lines = f.readlines()
            
        if len(lines) > self.max_lines:
            # Keep only the last max_lines
            with open(self.log_path, 'w') as f:
                f.writelines(lines[-self.max_lines:])
            print(f"[LOG] Log rotated: Kept last {self.max_lines} entries.")

if __name__ == "__main__":
    logger = INGRVMLogger()
    logger.log("SYSTEM_BOOT", {"msg": "INGRVM Logger initialized on Desktop."})
    print("✅ Log entry written to logs/node_activity.jsonl")

