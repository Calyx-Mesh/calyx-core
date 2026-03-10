import socket
import json
import argparse
import sys

class CortexCLI:
    """
    Phase 10: Cortex Orchestrator CLI.
    Simple client to interact with the local Cortex Bus.
    Used by headless agents to report status or request tasks.
    """
    def __init__(self, host='127.0.0.1', port=60006):
        self.host = host
        self.port = port

    def send_message(self, topic, payload):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                msg = json.dumps({"topic": topic, "payload": payload})
                s.sendall(msg.encode())
                print(f"📡 Sent to Cortex: {topic}")
        except ConnectionRefusedError:
            print("❌ Error: Cortex Bus is offline.")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cortex Swarm CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Publish Command
    pub_p = subparsers.add_parser("pub", help="Publish a message to the swarm")
    pub_p.add_argument("--topic", required=True, help="Message topic")
    pub_p.add_argument("--msg", required=True, help="Message content")

    # Task Command
    task_p = subparsers.add_parser("task", help="Inject a new swarm task")
    task_p.add_argument("--name", required=True, help="Task name")
    task_p.add_argument("--target", choices=["PC", "LAPTOP", "MOBILE"], default="PC")

    args = parser.parse_args()
    cli = CortexCLI()

    if args.command == "pub":
        cli.send_message(args.topic, {"text": args.msg})
    elif args.command == "task":
        # Simulates creating a task file that the Watchdog would see
        cli.send_message("task_inbox", {"file": f"SWARM_{args.target}_{args.name}.md", "status": "INJECTED"})
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
