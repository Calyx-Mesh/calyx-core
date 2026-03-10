import asyncio
import json
import os
import socket
import time
import sys
from typing import Dict, Any, Callable

# Add tools to path for The Judge
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
try:
    from the_judge import TheJudge
except ImportError:
    TheJudge = None

class CortexBus:
    """
    Task #16: Cortex Orchestrator Message Bus.
    Provides a high-speed local socket for headless agents to communicate.
    Acts as a bridge between the P2P Mesh and local Sub-Agents.
    """
    def __init__(self, socket_path="/tmp/cortex.sock", port=60006):
        self.socket_path = socket_path
        self.port = port
        self.is_unix = os.name != 'nt'
        self.subscribers: Dict[str, List[Callable]] = {}
        # Task #03: Swarm Bidding State
        self.active_agents: Dict[str, Dict] = {} # agent_id -> info
        self.pending_tasks: Dict[str, Dict] = {} # task_id -> bids
        self.judge = TheJudge(root_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) if TheJudge else None

    async def start_server(self):
        """ Starts the local message bus. """
        if self.is_unix:
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
            server = await asyncio.start_unix_server(self._handle_client, self.socket_path)
            print(f"🚀 Cortex Bus: Listening on Unix Socket {self.socket_path}")
        else:
            server = await asyncio.start_server(self._handle_client, '127.0.0.1', self.port)
            print(f"🚀 Cortex Bus: Listening on TCP 127.0.0.1:{self.port}")
        
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer):
        """ Handles incoming agent connections. """
        peer = writer.get_extra_info('peername')
        agent_id = f"agent_{peer[1]}" if peer else "local_agent"
        print(f"[CORTEX] New Agent Connected: {agent_id}")
        
        self.active_agents[agent_id] = {"writer": writer, "node_id": agent_id}

        try:
            while True:
                data = await reader.read(4096)
                if not data: break
                
                message = json.loads(data.decode())
                topic = message.get("topic", "default")
                payload = message.get("payload", {})
                
                # Task #03: Bidding / Registration
                if topic == "register":
                    self.active_agents[agent_id].update(payload)
                    if "node_id" in payload:
                        self.active_agents[agent_id]["node_id"] = payload["node_id"]
                elif topic == "bid":
                    task_id = payload.get("task_id")
                    if task_id in self.pending_tasks:
                        self.pending_tasks[task_id][agent_id] = payload.get("score", 0)

                # Phase 10 Task #01: Automated Verification
                elif topic == "task_done":
                    await self._verify_task_completion(agent_id, payload)

                # Existing: Task Triggering
                elif topic == "task_inbox":
                    await self._process_inbox_event(payload)

                # Notify subscribers
                if topic in self.subscribers:
                    for callback in self.subscribers[topic]:
                        await callback(payload)
                        
        except Exception as e:
            print(f"[CORTEX] Agent Error: {e}")
        finally:
            if agent_id in self.active_agents: del self.active_agents[agent_id]
            writer.close()
            await writer.wait_closed()

    async def _verify_task_completion(self, agent_id, payload):
        """ 
        Task #01: Trigger The Judge to verify the reported work.
        """
        task_id = payload.get("task_id")
        node_id = self.active_agents[agent_id].get("node_id", agent_id)
        changed_files = payload.get("changed_files", [])
        
        print(f"[CORTEX] TASK DONE: {task_id} reported by {node_id}. Triggering Audit...")
        
        if self.judge:
            # Run the audit in a thread to not block the bus
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self.judge.run_full_audit, changed_files, node_id)
            
            if success:
                print(f"✅ [CORTEX] Audit Passed for {task_id}.")
            else:
                print(f"❌ [CORTEX] Audit Failed for {task_id}. Node {node_id} slashed.")
        else:
            print(f"⚠️ [CORTEX] Judge not found. Skipping verification.")

    async def _process_inbox_event(self, payload):
        """ 
        Phase 10: Swarm Bidding Auction.
        Nodes compete for tasks based on VRAM and Reputation.
        """
        filename = payload.get("file")
        task_id = f"TASK_{int(time.time())}"
        print(f"[CORTEX] OPENING AUCTION: {filename} (ID: {task_id})")
        
        self.pending_tasks[task_id] = {}

        # 1. Call for Bids
        call_msg = json.dumps({
            "topic": "auction", 
            "payload": {
                "task_id": task_id, 
                "file": filename,
                "min_vram": 2.0 
            }
        })
        for agent in self.active_agents.values():
            agent["writer"].write(call_msg.encode())
            await agent["writer"].drain()

        # 2. Auction Window
        await asyncio.sleep(1.5)

        # 3. Multi-Factor Settlement
        bids = self.pending_tasks[task_id]
        if bids:
            # Winner is node with highest (VRAM * Reputation)
            winner = max(bids, key=bids.get)
            print(f"[CORTEX] AUCTION SETTLED: {winner} won {task_id} (Score: {bids[winner]:.2f})")
            
            # Send Assignment
            assign_msg = json.dumps({"topic": "assign", "payload": {"task_id": task_id, "file": filename}})
            self.active_agents[winner]["writer"].write(assign_msg.encode())
            await self.active_agents[winner]["writer"].drain()
        else:
            print(f"[CORTEX] NO BIDS: Defaulting to local PC_MASTER logic.")

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    async def publish(self, topic: str, payload: Any):
        """ Local broadcast to all connected agents (Mock for now). """
        pass

if __name__ == "__main__":
    bus = CortexBus()
    async def sample_callback(data):
        print(f"CALLBACK TRIGGERED: {data}")

    bus.subscribe("neural_spike", sample_callback)
    try:
        asyncio.run(bus.start_server())
    except KeyboardInterrupt:
        pass
