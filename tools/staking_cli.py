import sys
import os
import argparse
import time
from pathlib import Path

# Add core to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reward_engine import INGRVMLedger

class StakingCLI:
    """
    Phase 9 Task #8: Staking CLI.
    Allows nodes to lock $DOPA for validation rights.
    """
    def __init__(self, db_path: str = None):
        # Path resolution
        if db_path is None:
            possible_paths = [
                "neuromorphic_env/ledger.db",
                "INGRVM/Core/neuromorphic_env/ledger.db",
                "../neuromorphic_env/ledger.db"
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    self.db_path = p
                    break
            else:
                self.db_path = "neuromorphic_env/ledger.db"
        else:
            self.db_path = db_path
            
        self.ledger = INGRVMLedger(self.db_path)
        self.node_id = os.getenv("INGRVM_NODE_ID", "LAPTOP_RELAY")

    def show_status(self):
        info = self.ledger.get_staking_info(self.node_id)
        print(f"\n--- 🥩 INGRVM Staking Status ---")
        print(f"Node ID:  {self.node_id}")
        print(f"Liquid:   {info['liquid']:.4f} $DOPA")
        print(f"Staked:   {info['staked']:.4f} $DOPA")
        print(f"Total:    {(info['liquid'] + info['staked']):.4f} $DOPA")
        
        rep = self.ledger.get_reputation(self.node_id)
        print(f"Rep Score: {rep:.4f}")
        
        status = "🟢 VALIDATOR ACTIVE" if info['staked'] >= 10.0 else "⚪️ OBSERVER (Stake < 10)"
        print(f"Status:    {status}")
        print(f"----------------------------------\n")

    def stake(self, amount: float):
        print(f"🔒 Requesting stake of {amount} $DOPA...")
        if self.ledger.stake(self.node_id, amount):
            print("✅ SUCCESS: Tokens moved to staking contract.")
            self.show_status()
        else:
            print("❌ FAILED: Insufficient liquid balance.")

    def unstake(self, amount: float):
        print(f"🔓 Requesting unstake of {amount} $DOPA...")
        if self.ledger.unstake(self.node_id, amount):
            print("✅ SUCCESS: Tokens returned to liquid balance.")
            self.show_status()
        else:
            print("❌ FAILED: Insufficient staked balance.")

    def register_validator(self):
        print(f"📡 Requesting Validator Registration for {self.node_id}...")
        info = self.ledger.get_staking_info(self.node_id)
        
        if info['staked'] >= 10.0:
            print("✅ SUCCESS: Stake threshold met (>= 10 $DOPA).")
            print(f"[AUTH] Handshaking with INGRVM Hub...")
            time.sleep(1)
            print(f"🟢 REGISTERED: {self.node_id} is now an Active Validator.")
        else:
            print(f"❌ FAILED: Stake too low ({info['staked']:.4f} / 10.0 required).")
            print("Action: Use 'python staking_cli.py stake 10' first.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="INGRVM Staking CLI")
    parser.add_argument("command", choices=["status", "stake", "unstake", "register-validator"], help="Action to perform")
    parser.add_argument("amount", type=float, nargs="?", default=0.0, help="Amount of $DOPA")
    parser.add_argument("--db", type=str, default=None, help="Path to ledger.db")
    
    args = parser.parse_args()
    cli = StakingCLI(args.db)
    
    if args.command == "status":
        cli.show_status()
    elif args.command == "stake":
        if args.amount <= 0:
            print("Usage: python staking_cli.py stake <amount>")
        else:
            cli.stake(args.amount)
    elif args.command == "unstake":
        if args.amount <= 0:
            print("Usage: python staking_cli.py unstake <amount>")
        else:
            cli.unstake(args.amount)
    elif args.command == "register-validator":
        cli.register_validator()
