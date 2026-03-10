import sqlite3
import time
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys_path = Path(__file__).parent.parent.parent.absolute()
load_dotenv(sys_path / "INGRVM" / ".env")

class BridgeRelayerService:
    """
    Phase 9: Sovereign Bridge Relayer Service.
    Actively monitors the INGRVMLedger for mesh exit events ($DOPA -> Public).
    """
    def __init__(self, db_path: str = None):
        # Handle path resolution from different run locations
        if db_path is None:
            possible_paths = [
                "neuromorphic_env/ledger.db",
                "INGRVM/Core/neuromorphic_env/ledger.db",
                "../../neuromorphic_env/ledger.db",
                "../neuromorphic_env/ledger.db"
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    self.db_path = p
                    break
            else:
                self.db_path = "neuromorphic_env/ledger.db" # Default
        else:
            self.db_path = db_path
            
        # Resolved directory for JSON state
        base_dir = os.path.dirname(self.db_path) if self.db_path else "neuromorphic_env"
        self.processed_tx_file = os.path.join(base_dir, "bridge_processed.json")
        self.processed_txs = self._load_processed()
        self.token_symbol = os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        
    def _load_processed(self):
        if os.path.exists(self.processed_tx_file):
            try:
                with open(self.processed_tx_file, "r") as f:
                    return set(json.load(f))
            except Exception: return set()
        return set()

    def _save_processed(self):
        try:
            os.makedirs(os.path.dirname(self.processed_tx_file), exist_ok=True)
            with open(self.processed_tx_file, "w") as f:
                json.dump(list(self.processed_txs), f)
        except Exception as e:
            print(f"❌ Error saving processed TX log: {e}")

    def scan_for_burns(self):
        """ Scans the ledger for tokens being 'exited' to the public market. """
        if not os.path.exists(self.db_path):
            return 0

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # We look for SLASH transactions to BURN_ADDRESS which indicate a Bridge Exit
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE tx_type = 'SLASH' 
                AND receiver_id = 'BURN_ADDRESS'
                ORDER BY tx_id ASC
            """)
            
            burns = cursor.fetchall()
            new_burns_found = 0
            
            for tx in burns:
                tx_id = tx['tx_id']
                if tx_id in self.processed_txs:
                    continue

                # Execute the simulated cross-chain mint
                self._execute_cross_chain_mint(tx)
                self.processed_txs.add(tx_id)
                new_burns_found += 1

            conn.close()
            if new_burns_found > 0:
                self._save_processed()
            return new_burns_found
        except Exception as e:
            print(f"❌ Ledger scan error: {e}")
            return 0

    def _execute_cross_chain_mint(self, tx):
        """ Simulates calling a Smart Contract on Ethereum/Solana. """
        amount = abs(tx['amount'])
        sender = tx['sender_id']
        memo = tx['memo'] or "No target address provided"
        ts = tx['timestamp']
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🌉 CROSS-CHAIN MINT TRIGGERED")
        print(f"  ID:      {tx['tx_id']}")
        print(f"  Amount:  {amount} ${self.token_symbol}")
        print(f"  Node:    {sender[:16]}...")
        print(f"  Target:  {memo}")
        print(f"  Status:  [MINTED] 1:1 asset issued on Public Chain.")
        print(f"  Proof:   sha256({ts}_{tx['tx_id']})")
        print("-" * 40)

def run_service(poll_interval=5):
    relayer = BridgeRelayerService()
    print(f"--- 🌉 INGRVM Bridge Relayer (Active Service) ---")
    print(f"Monitoring: {relayer.db_path}")
    print(f"Token:      ${relayer.token_symbol}")
    print(f"Polling:    Every {poll_interval}s\n")
    
    try:
        while True:
            new_count = relayer.scan_for_burns()
            if new_count > 0:
                print(f"✅ Processed {new_count} new exit events.")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n🛑 Relayer Service stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="INGRVM Sovereign Bridge Relayer")
    parser.add_argument("--poll", type=int, default=0, help="Run as service with given interval (seconds)")
    parser.add_argument("--db", type=str, default=None, help="Path to ledger.db")
    args = parser.parse_args()

    if args.poll > 0:
        run_service(args.poll)
    else:
        # Single scan mode
        relayer = BridgeRelayerService(args.db)
        count = relayer.scan_for_burns()
        if count == 0:
            print("💤 No new burn events detected.")
        else:
            print(f"✅ Finished. {count} new exits processed.")
