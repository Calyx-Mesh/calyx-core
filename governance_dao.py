import sqlite3
import time
import os
import sys
import argparse
import requests
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from reward_engine import INGRVMLedger
from config import INGRVMConfig
from dotenv import load_dotenv

# Load env for Hub URL
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
HUB_URL = os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")

class Proposal(BaseModel):
    proposal_id: str
    description: str
    target_ingrvm: str
    new_weights_hash: str
    options: List[str] = ["ACCEPT", "REJECT"]
    status: str = "OPEN"
    voting_type: str = "WEIGHTED"
    created_at: float = Field(default_factory=time.time)

class INGRVMDAO:
    """
    Phase 6 Foundation: SQL-backed Governance DAO.
    Tracks network proposals and node votes.
    """
    def __init__(self, ledger: INGRVMLedger, config: INGRVMConfig, db_path: str = "neuromorphic_env/governance.db"):
        self.ledger = ledger
        self.config = config
        self.db_path = db_path
        self.token_symbol = os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Proposals Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id TEXT PRIMARY KEY,
                proposer_id TEXT NOT NULL,
                description TEXT NOT NULL,
                target_ingrvm TEXT,
                new_weights_hash TEXT,
                status TEXT DEFAULT 'OPEN', -- OPEN, ACCEPTED, REJECTED
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Votes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                proposal_id TEXT NOT NULL,
                peer_id TEXT NOT NULL,
                vote TEXT NOT NULL, -- YES, NO
                weight REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (proposal_id, peer_id),
                FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
            )
        """)
        
        conn.commit()
        conn.close()

    def create_proposal(self, proposer_id: str, description: str, target_ingrvm: str, weights_hash: str) -> Optional[str]:
        """ Nodes with > 0.8 rep can create proposals. """
        rep = self.ledger.get_reputation(proposer_id)
        if rep < 0.8:
            print(f"[DAO] REJECTED: {proposer_id} reputation ({rep:.2f}) too low to propose.")
            return None
            
        p_id = f"PROP_{int(time.time())}_{proposer_id[:4]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO proposals (proposal_id, proposer_id, description, target_ingrvm, new_weights_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (p_id, proposer_id, description, target_ingrvm, weights_hash))
        conn.commit()
        conn.close()
        
        print(f"[DAO] Proposal Created: {p_id}")
        return p_id

    def cast_vote(self, peer_id: str, proposal_id: str, vote: str):
        """ Casts a weighted vote based on reputation. """
        weight = self.ledger.get_reputation(peer_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO votes (proposal_id, peer_id, vote, weight)
            VALUES (?, ?, ?, ?)
        """, (proposal_id, peer_id, vote, weight))
        conn.commit()
        conn.close()
        
        print(f"[DAO] Vote Cast: {peer_id} voted {vote} on {proposal_id} (Weight: {weight:.2f})")

    def tally_votes(self, proposal_id: str) -> Tuple[str, float]:
        """ Aggregates votes and determines status. """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            conn.close()
            return "NOT_FOUND", 0.0

        cursor.execute("SELECT vote, SUM(weight) FROM votes WHERE proposal_id = ? GROUP BY vote", (proposal_id,))
        results = dict(cursor.fetchall())
        
        yes_weight = results.get("YES", 0.0)
        no_weight = results.get("NO", 0.0)
        total = yes_weight + no_weight
        
        if total == 0: 
            conn.close()
            return "OPEN", 0.0
        
        confidence = (yes_weight / total) * 100
        status = "ACCEPTED" if yes_weight > no_weight else "REJECTED"
        
        # Update proposal status
        cursor.execute("UPDATE proposals SET status = ? WHERE proposal_id = ?", (status, proposal_id))
        conn.commit()
        conn.close()
        
        # Task #15: Automate Parameter Updates
        if status == "ACCEPTED":
            self._apply_proposal_effects(prop)
            
        print(f"[DAO] {proposal_id} Tally: {status} (Confidence: {confidence:.2f}%)")
        return status, confidence

    def _apply_proposal_effects(self, prop: sqlite3.Row):
        """ Task #15: Executes the technical and financial changes from a passed proposal. """
        desc = prop['description'].lower()
        
        # 1. Config Parameter Updates (Task #15)
        if "set " in desc and " to " in desc:
            try:
                parts = desc.split("set ")[1].split(" to ")
                param_path = parts[0].strip() # "economy.spike_cost_joules"
                new_value = parts[1].strip()
                
                section, key = param_path.split(".")
                try: val = float(new_value)
                except: val = new_value
                
                self.config.set(section, key, val)
                print(f"[DAO-AUTO] Automation applied: {param_path} = {val}")
            except Exception as e:
                print(f"[DAO-AUTO] Failed to parse automation: {e}")

        # 2. Financial Execution (Task #09: On-Chain Executor)
        if "mint " in desc or "transfer " in desc:
            self._execute_financial_action(desc, prop['proposal_id'])

    def _execute_financial_action(self, desc: str, p_id: str):
        """ 
        Task #09: The Executor.
        Parses and executes $DOPA movements approved by the mesh.
        Example: "Mint 500 to HUB_NODE" or "Transfer 100 from SYSTEM to LAPTOP_RELAY"
        """
        try:
            if "mint " in desc:
                # Format: "mint [amount] to [node_id]"
                parts = desc.split("mint ")[1].split(" to ")
                amount = float(parts[0].strip())
                target = parts[1].strip().upper()
                self.ledger.mint_rewards(target, amount, memo=f"DAO Execution: {p_id}")
                print(f"[DAO-EXEC] SUCCESS: Minted {amount} ${self.token_symbol} to {target}")

            elif "transfer " in desc:
                # Format: "transfer [amount] from [sender] to [receiver]"
                parts = desc.split("transfer ")[1].split(" from ")
                amount = float(parts[0].strip())
                sub_parts = parts[1].split(" to ")
                sender = sub_parts[0].strip().upper()
                receiver = sub_parts[1].strip().upper()

                if self.ledger.transfer(sender, receiver, amount):
                    print(f"[DAO-EXEC] SUCCESS: Transferred {amount} ${self.token_symbol}: {sender} -> {receiver}")
                else:
                    print(f"[DAO-EXEC] FAILED: Insufficient funds or invalid nodes for transfer.")

            elif "slash " in desc:
                # Format: "slash [amount] from [node_id]"
                parts = desc.split("slash ")[1].split(" from ")
                amount = float(parts[0].strip())
                target = parts[1].strip().upper()
                self.ledger.burn_stake(target, amount, memo=f"DAO Slashing: {p_id}")
                print(f"[DAO-EXEC] SUCCESS: Slashed {amount} ${self.token_symbol} from {target} stake.")

        except Exception as e:
            print(f"[DAO-EXEC] Execution Error: {e}")

    def get_proposals(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proposals ORDER BY created_at DESC")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def sync_global_votes(self, remote_hub_url: str, proposal_id: str):
        """ 
        Task #14: Global Tally Service.
        Synchronizes votes from a remote Hub to ensure global consensus.
        """
        print(f"[DAO-GLOBAL] Syncing votes for {proposal_id} from {remote_hub_url}")
        try:
            resp = requests.get(f"{remote_hub_url}/api/dao/votes/{proposal_id}", timeout=5)
            if resp.status_code == 200:
                remote_votes = resp.json()
                for v in remote_votes:
                    # Record the remote vote locally
                    self.cast_vote(
                        peer_id=v['peer_id'],
                        proposal_id=proposal_id,
                        vote=v['vote']
                    )
                print(f"[DAO-GLOBAL] Successfully merged {len(remote_votes)} remote votes.")
        except Exception as e:
            print(f"[DAO-GLOBAL] Sync failed: {e}")

    def get_votes_for_proposal(self, proposal_id: str) -> List[Dict[str, Any]]:
        """ Returns all recorded votes for a specific proposal. """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM votes WHERE proposal_id = ?", (proposal_id,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

def main():
    parser = argparse.ArgumentParser(description="INGRVM Governance DAO CLI")
    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List active network proposals")

    # Vote command
    vote_p = subparsers.add_parser("vote", help="Cast a vote on a proposal")
    vote_p.add_argument("--id", required=True, help="Proposal ID")
    vote_p.add_argument("--choice", required=True, choices=["YES", "NO"], help="Your vote")
    vote_p.add_argument("--peer", default=os.getenv("INGRVM_NODE_ID", "LAPTOP_RELAY"), help="Your Peer ID")

    args = parser.parse_args()

    if args.command == "list":
        print(f"--- Fetching Proposals from Hub: {HUB_URL} ---")
        try:
            resp = requests.get(f"{HUB_URL}/api/dao/proposals", timeout=3)
            props = resp.json()
            if not props:
                print("No active proposals.")
            for p in props:
                print(f"[{p['status']}] {p['proposal_id']}: {p['description']}")
        except Exception as e:
            print(f"❌ Error fetching proposals: {e}")

    elif args.command == "vote":
        print(f"--- Casting Vote to Hub: {HUB_URL} ---")
        payload = {
            "peer_id": args.peer,
            "proposal_id": args.id,
            "vote": args.choice
        }
        try:
            resp = requests.post(f"{HUB_URL}/api/dao/vote", json=payload, timeout=3)
            if resp.status_code == 200:
                print(f"✅ SUCCESS: {resp.json()}")
            else:
                print(f"❌ FAILED: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Error casting vote: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()


