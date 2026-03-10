import os
import sys
import json
import time
import socket
import subprocess

# Add Infrastructure to path for cortex discovery
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Infrastructure'))

class HeadlessGemini:
    """
    Session 42: Headless Swarm Processor.
    Simulates a resident Gemini agent that listens to the Cortex Bus
    to autonomously execute and verify mesh tasks.
    """
    def __init__(self, agent_id="PC_MASTER_HEADLESS", bus_port=60006):
        self.agent_id = agent_id
        self.bus_port = bus_port
        self.is_running = True

    def _connect_to_bus(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', self.bus_port))
            return s
        except Exception as e:
            print(f"[HEADLESS] Bus connection failed: {e}")
            return None

    def run(self):
        print(f"🧠 [HEADLESS] Gemini Swarm Agent Active: {self.agent_id}")
        
        while self.is_running:
            sock = self._connect_to_bus()
            if not sock:
                time.sleep(5)
                continue
                
            try:
                # 1. Register with the Bus
                reg_msg = json.dumps({
                    "topic": "register", 
                    "payload": {"agent_id": self.agent_id, "vram": 11.0, "type": "HEADLESS"}
                })
                sock.sendall(reg_msg.encode())
                
                while True:
                    data = sock.recv(4096)
                    if not data: break
                    
                    msg = json.loads(data.decode())
                    topic = msg.get("topic")
                    payload = msg.get("payload", {})
                    
                    if topic == "auction":
                        task_id = payload.get("task_id")
                        print(f"🎲 [BIDDING] Submitting bid for Task: {task_id}")
                        bid_msg = json.dumps({
                            "topic": "bid",
                            "payload": {"task_id": task_id, "score": 1.95} # High score for PC
                        })
                        sock.sendall(bid_msg.encode())
                        
                    elif topic == "assign":
                        task_id = payload.get("task_id")
                        filename = payload.get("file")
                        print(f"🔥 [EXECUTION] Processing Assigned Task: {task_id} ({filename})")
                        self.process_task(task_id, filename)
                        
            except Exception as e:
                print(f"[HEADLESS] Connection error: {e}")
            finally:
                sock.close()
                time.sleep(2)

    def process_task(self, task_id, filename):
        """ Simulates the autonomous work loop. """
        print(f"⏳ [WORK] Thinking... (Task: {task_id})")
        time.sleep(3) # Simulate compute
        
        # In a real scenario, this agent would use the Gemini CLI 
        # to modify files and then run The Judge.
        print(f"⚖️ [VERIFY] Running Judge on modified state...")
        
        # Trigger local judge audit (Mocking for PoC)
        print(f"✅ [SUCCESS] Task {task_id} completed and verified.")

if __name__ == "__main__":
    agent = HeadlessGemini()
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[HEADLESS] Powering down brain...")
