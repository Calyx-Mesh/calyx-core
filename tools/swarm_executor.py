import os
import sys
import json
import time
import socket
import subprocess
from tools.hardware_ranker import HardwareRanker

# Add Core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class SwarmExecutor:
    """
    Phase 10 Task #5: Headless Task Processor.
    Listens to the Cortex Bus for 'assign' topics and executes the task.
    Integrates the 'Judge' for final verification before reporting success.
    """
    def __init__(self, agent_id="PC_MASTER", bus_host="127.0.0.1", bus_port=60006):
        self.agent_id = agent_id
        self.bus_host = bus_host
        self.bus_port = bus_port
        self.is_running = True
        self.ranker = HardwareRanker()
        self.tier_report = self.ranker.get_rank_report()

    def _send_to_bus(self, topic, payload):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.bus_host, self.bus_port))
                msg = json.dumps({"topic": topic, "payload": payload})
                s.sendall(msg.encode())
        except Exception as e:
            pass # Bus might be temporary offline

    def register(self):
        """ Registers this agent with the Cortex Bus. """
        print(f"[EXECUTOR] Registering {self.agent_id} (Tier {self.tier_report['tier']})...")
        self._send_to_bus("register", {
            "agent_id": self.agent_id,
            "tier": self.tier_report["tier"],
            "resources": self.tier_report["hardware"]
        })

    def run(self):
        """ Main loop: Listen for assignments via a persistent connection. """
        print(f"[EXECUTOR] Headless Swarm Node Active: {self.agent_id}")
        self.register()
        
        while self.is_running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.bus_host, self.bus_port))
                    # Wait for data
                    while True:
                        data = s.recv(4096)
                        if not data: break
                        
                        msg = json.loads(data.decode())
                        topic = msg.get("topic")
                        payload = msg.get("payload", {})
                        
                        if topic == "auction":
                            # Task #03: Submit a dynamic bid based on Tier!
                            task_id = payload.get('task_id')
                            print(f"[EXECUTOR] AUCTION DETECTED: {task_id}")
                            
                            # Base score (reputation placeholder) * hardware multiplier
                            base_score = 1.0
                            final_score = base_score * self.tier_report["bid_multiplier"]
                            
                            self._send_to_bus("bid", {
                                "task_id": task_id,
                                "score": final_score
                            })
                            print(f"[EXECUTOR] BID SUBMITTED: {final_score:.2f} (Tier {self.tier_report['tier']})")
                            
                        elif topic == "assign":
                            # Task #05: Execute Task
                            task_id = payload.get("task_id")
                            filename = payload.get("file")
                            print(f"🚀 [EXECUTOR] TASK ASSIGNED: {task_id} -> {filename}")
                            self.execute_task(task_id, filename)
                            
            except Exception as e:
                print(f"[EXECUTOR] Connection lost, retrying in 5s... ({e})")
                time.sleep(5)

    def execute_task(self, task_id, filename):
        """ Simulates the headless Gemini processing. """
        print(f"[EXECUTOR] Executing {task_id}...")
        
        # 1. Simulate "Thinking"
        time.sleep(2)
        
        # 2. Run The Judge on the changed environment
        from tools.the_judge import TheJudge
        judge = TheJudge(root_dir="../")
        # In a real task, we'd know which files changed. 
        # For this headless demo, we audit the executor itself.
        success = judge.run_full_audit([f"tools/{os.path.basename(__file__)}"], node_id=self.agent_id)
        
        if success:
            print(f"✅ [EXECUTOR] Task {task_id} Complete. Audit Passed.")
            self._send_to_bus("task_done", {"task_id": task_id, "status": "SUCCESS"})
        else:
            print(f"❌ [EXECUTOR] Task {task_id} FAILED Audit.")
            self._send_to_bus("task_done", {"task_id": task_id, "status": "FAILED"})

if __name__ == "__main__":
    node_id = os.getenv("INGRVM_NODE_ID", "PC_MASTER")
    executor = SwarmExecutor(agent_id=node_id)
    executor.run()

