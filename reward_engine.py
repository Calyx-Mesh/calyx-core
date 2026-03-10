import sqlite3
import time
import os
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from zk_proof_generator import ZKProofGenerator

class NodeStats(BaseModel):
    peer_id: str
    useful_work_spikes: int = 0
    reputation_score: float = 1.0 # q_i in whitepaper
    last_active: float = Field(default_factory=time.time)

class RewardEngine:
    """
    Implements the INGRVM Tokenomics.
    Formula: R_i = E * (w_i * q_i) / Sum(w_j * q_j)
    Includes dynamic inflation to scale with network size.
    """
    def __init__(self, epoch_emission: float = 100.0, inflation_rate: float = 0.05):
        self.epoch_emission = epoch_emission
        self.inflation_rate = inflation_rate
        self.nodes: Dict[str, NodeStats] = {}

    def adjust_inflation(self, active_node_count: int):
        """
        Adjusts emissions based on network density.
        """
        if active_node_count > 50: # Threshold for 'Growth' phase
            self.epoch_emission *= (1.0 - self.inflation_rate)
            print(f"[ECONOMY] Inflation Brake: Emission set to {self.epoch_emission:.2f}")
        else:
            self.epoch_emission *= (1.0 + (self.inflation_rate / 2))
            print(f"[ECONOMY] Growth Stimulus: Emission set to {self.epoch_emission:.2f}")

    def register_work(self, peer_id: str, spikes: int):
        if peer_id not in self.nodes:
            self.nodes[peer_id] = NodeStats(peer_id=peer_id)

        self.nodes[peer_id].useful_work_spikes += spikes
        self.nodes[peer_id].last_active = time.time()

        # Reputation boost for active work
        self.nodes[peer_id].reputation_score = min(2.0, self.nodes[peer_id].reputation_score + 0.01)

    def distribute_mesh_rewards(self, shard_contributions: Dict[str, int], total_task_spikes: int):
        """
        Task #14: Multi-node Reward Splitting.
        Distributes spikes for a single inference task across all participating nodes.
        """
        total_layers = sum(shard_contributions.values())
        if total_layers == 0: return

        for node_id, layers in shard_contributions.items():
            work_proportion = layers / total_layers
            node_share = int(total_task_spikes * work_proportion)

            self.register_work(node_id, spikes=max(1, node_share))
            print(f"[REWARDS] Distributed {node_share} spikes to {node_id} for mesh contribution.")

    def calculate_payouts(self) -> Dict[str, float]:
        """Calculates the $DOPA distribution for the current epoch."""
        payouts = {}

        # Calculate denominator: Sum of (work * quality) for all nodes
        total_utility_weighted_work = sum(
            node.useful_work_spikes * node.reputation_score
            for node in self.nodes.values()
        )

        if total_utility_weighted_work == 0:
            return {peer_id: 0.0 for peer_id in self.nodes}

        for peer_id, node in self.nodes.items():
            # R_i formula
            node_utility = node.useful_work_spikes * node.reputation_score
            reward = self.epoch_emission * (node_utility / total_utility_weighted_work)
            payouts[peer_id] = round(reward, 4)

        return payouts

class INGRVMLedger:
    """
    Phase 9 Sovereign Mainnet: Merkle-Tree Ledger v2.
    Transitions from simple SQL tracking to a verifiable block-based history.
    """
    def __init__(self, db_path: str = "neuromorphic_env/ledger.db"):
        self.db_path = db_path
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._ensure_genesis()
        self.token_symbol = os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        self.zk_verifier = ZKProofGenerator()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Accounts Table (Current Balances)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                node_id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                staked_balance REAL DEFAULT 0.0,
                reputation REAL DEFAULT 1.0,
                total_work_spikes INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Schema Migration: Add staked_balance if it doesn't exist (Legacy compatibility)
        try:
            cursor.execute("ALTER TABLE accounts ADD COLUMN staked_balance REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass # Already exists

        # 2. Transactions Table (History)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                receiver_id TEXT,
                amount REAL,
                tx_type TEXT, -- 'MINT', 'TRANSFER', 'REWARD', 'SLASH', 'STAKE', 'UNSTAKE'
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                memo TEXT,
                block_id INTEGER DEFAULT -1 -- Linked to a verified block
            )
        """)

        # 3. Blocks Table (Verifiable Chain)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prev_hash TEXT,
                merkle_root TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                nonce INTEGER DEFAULT 0,
                block_hash TEXT UNIQUE
            )
        """)
        
        conn.commit()
        conn.close()

    def _hash_block(self, prev_hash: str, merkle_root: str, ts: str, nonce: int) -> str:
        block_content = f"{prev_hash}{merkle_root}{ts}{nonce}"
        return hashlib.sha256(block_content.encode()).hexdigest()

    def _ensure_genesis(self):
        """ Task #1: Create Genesis block for Merkle-Tree Ledger v2. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM blocks")
        if cursor.fetchone()[0] == 0:
            print("[LEDGER] Initializing Sovereign Mainnet: Creating Genesis Block...")
            prev_hash = "0" * 64
            merkle_root = hashlib.sha256(b"INGRVM_GENESIS_TRANSACTION_ZERO").hexdigest()
            ts = str(time.time())
            nonce = 42 # Lucky number
            
            genesis_hash = self._hash_block(prev_hash, merkle_root, ts, nonce)
            
            cursor.execute("""
                INSERT INTO blocks (prev_hash, merkle_root, timestamp, nonce, block_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (prev_hash, merkle_root, ts, nonce, genesis_hash))
            
            # Initialize System Node (PC_MASTER) with bootstrap supply
            # Inline mint_rewards to use the SAME connection/transaction
            cursor.execute("""
                INSERT INTO accounts (node_id, balance) VALUES (?, ?)
                ON CONFLICT(node_id) DO UPDATE SET 
                    balance = balance + EXCLUDED.balance,
                    last_updated = CURRENT_TIMESTAMP
            """, ("PC_MASTER_HUB", 1000.0))
            
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
                VALUES (?, ?, ?, ?, ?)
            """, ("SYSTEM", "PC_MASTER_HUB", 1000.0, "MINT", "Genesis Bootstrap Emission"))
            
            conn.commit()
            print(f"[LEDGER] GENESIS BLOCK CREATED: {genesis_hash[:16]}...")
        conn.close()

    def mint_rewards(self, peer_id: str, amount: float, memo: str = "Epoch Reward"):
        """ Mints new $DOPA and assigns it to a node. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute("""
            INSERT INTO accounts (node_id, balance) VALUES (?, ?)
            ON CONFLICT(node_id) DO UPDATE SET 
                balance = balance + EXCLUDED.balance,
                last_updated = CURRENT_TIMESTAMP
        """, (peer_id, amount))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
            VALUES (?, ?, ?, ?, ?)
        """, ("SYSTEM", peer_id, amount, "MINT", memo))
        
        conn.commit()
        conn.close()
        print(f"[LEDGER] Minted {amount:.4f} ${self.token_symbol} to {peer_id[:12]}... ({memo})")

    def transfer(self, sender_id: str, receiver_id: str, amount: float) -> bool:
        """ Transfers $DOPA between two nodes. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check balance
        cursor.execute("SELECT balance FROM accounts WHERE node_id = ?", (sender_id,))
        row = cursor.fetchone()
        if not row or row[0] < amount:
            conn.close()
            return False
            
        # Execute atomic transfer
        try:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE node_id = ?", (amount, sender_id))
            cursor.execute("""
                INSERT INTO accounts (node_id, balance) VALUES (?, ?)
                ON CONFLICT(node_id) DO UPDATE SET balance = balance + EXCLUDED.balance
            """, (receiver_id, amount))
            
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type)
                VALUES (?, ?, ?, ?)
            """, (sender_id, receiver_id, amount, "TRANSFER"))
            
            conn.commit()
            success = True
        except Exception:
            conn.rollback()
            success = False
        finally:
            conn.close()
        return success

    def verify_and_record_work(self, peer_id: str, spikes: int, poi_packet: Optional[Dict], model_id: str = "INGRVM-1.0"):
        """ 
        Task #01/09: Verifies work via zk-PoI before recording.
        If proof is invalid, the node is slashed.
        """
        if not poi_packet:
            print(f"[LEDGER] REJECTED: No PoI packet from {peer_id}. Slashing...")
            self.slash_node(peer_id, penalty_syn=2.0, rep_burn=0.05, memo="Missing PoI Packet")
            return False

        is_valid = self.zk_verifier.verify_poi(poi_packet, model_id)
        if is_valid:
            print(f"[LEDGER] PoI Verified for {peer_id}. Recording {spikes} spikes.")
            self.record_work(peer_id, spikes)
            return True
        else:
            print(f"[LEDGER] FRAUD DETECTED: Invalid PoI from {peer_id}. Slashing...")
            self.slash_node(peer_id, penalty_syn=10.0, rep_burn=0.2, memo="Invalid zk-PoI Proof")
            return False

    def record_work(self, peer_id: str, spikes: int):
        """ Updates a node's work statistics and reputation. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Reputation grows with work (max 2.0)
        cursor.execute("""
            INSERT INTO accounts (node_id, total_work_spikes, reputation) VALUES (?, ?, 1.01)
            ON CONFLICT(node_id) DO UPDATE SET 
                total_work_spikes = total_work_spikes + EXCLUDED.total_work_spikes,
                reputation = MIN(2.0, reputation + 0.005),
                last_updated = CURRENT_TIMESTAMP
        """, (peer_id, spikes))
        
        conn.commit()
        conn.close()

    def slash_node(self, peer_id: str, penalty_syn: float = 5.0, rep_burn: float = 0.1, memo: str = "Validation Failure"):
        """ 
        Phase 6 Task #16: Reputation Burn (Slashing).
        Penalizes a node for malicious or incorrect behavior.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 0. Ensure account exists (default 0 balance, 1.0 rep)
        cursor.execute("INSERT OR IGNORE INTO accounts (node_id, balance, reputation) VALUES (?, 0.0, 1.0)", (peer_id,))

        # 1. Reduce Balance (Minimum 0)
        cursor.execute("""
            UPDATE accounts 
            SET balance = MAX(0.0, balance - ?),
                reputation = MAX(0.5, reputation - ?),
                last_updated = CURRENT_TIMESTAMP
            WHERE node_id = ?
        """, (penalty_syn, rep_burn, peer_id))
        
        # 2. Record Slashed Transaction
        cursor.execute("""
            INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
            VALUES (?, ?, ?, ?, ?)
        """, (peer_id, "BURN_ADDRESS", -penalty_syn, "SLASH", memo))
        
        conn.commit()
        conn.close()
        print(f"[LEDGER] SLASHTAG: {peer_id[:12]}... Burned {penalty_syn} $DOPA. Rep Burn: -{rep_burn}")

    def get_reputation(self, node_id: str) -> float:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT reputation FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 1.0

    def get_balance(self, node_id: str) -> float:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0.0

    def get_top_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts ORDER BY balance DESC LIMIT ?", (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def stake(self, node_id: str, amount: float) -> bool:
        """ 
        Task #08: Locks $DOPA into staked_balance for validation rights.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Check liquid balance
        cursor.execute("SELECT balance FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        if not row or row[0] < amount:
            conn.close()
            return False
            
        try:
            # 2. Atomic Stake
            cursor.execute("UPDATE accounts SET balance = balance - ?, staked_balance = staked_balance + ? WHERE node_id = ?", (amount, amount, node_id))
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
                VALUES (?, ?, ?, ?, ?)
            """, (node_id, "STAKING_CONTRACT", amount, "STAKE", "Locking for validation"))
            conn.commit()
            success = True
        except Exception:
            conn.rollback()
            success = False
        finally:
            conn.close()
        return success

    def unstake(self, node_id: str, amount: float) -> bool:
        """ Unlocks $DOPA from staked_balance. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Check staked balance
        cursor.execute("SELECT staked_balance FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        if not row or row[0] < amount:
            conn.close()
            return False
            
        try:
            # 2. Atomic Unstake
            cursor.execute("UPDATE accounts SET staked_balance = staked_balance - ?, balance = balance + ? WHERE node_id = ?", (amount, amount, node_id))
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
                VALUES (?, ?, ?, ?, ?)
            """, ("STAKING_CONTRACT", node_id, amount, "UNSTAKE", "Unlocking tokens"))
            conn.commit()
            success = True
        except Exception:
            conn.rollback()
            success = False
        finally:
            conn.close()
        return success

    def get_staking_info(self, node_id: str) -> Dict[str, float]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT balance, staked_balance FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"liquid": row[0], "staked": row[1]}
        return {"liquid": 0.0, "staked": 0.0}

    def burn_stake(self, node_id: str, amount: float, memo: str = "Slashing Burn"):
        """ 
        Task #12: Permanently removes $DOPA from a node's stake.
        Used for Slashing Consensus.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE accounts SET staked_balance = MAX(0.0, staked_balance - ?) WHERE node_id = ?", (amount, node_id))
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
                VALUES (?, ?, ?, ?, ?)
            """, (node_id, "BURN_ADDRESS", -amount, "SLASH", memo))
            conn.commit()
            print(f"[LEDGER] Burned {amount} $DOPA from {node_id} stake. Reason: {memo}")
        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to burn stake: {e}")
        finally:
            conn.close()

# --- Verification Test ---
if __name__ == "__main__":
    # 1. Test Ledger Logic
    ledger = INGRVMLedger()
    test_node = "12D3KooW_MASTER_NODE_ALPHA"
    ledger.record_work(test_node, spikes=1000)
    ledger.mint_rewards(test_node, amount=50.0, memo="Bootstrap Bonus")
    
    # 2. Test Reward Engine Logic
    engine = RewardEngine(epoch_emission=1000.0)
    engine.register_work("12D3KooW_PC_BACKBONE", spikes=5000)
    engine.nodes["12D3KooW_PC_BACKBONE"].reputation_score = 1.8
    engine.register_work("12D3KooW_PIXEL_8", spikes=1200)
    
    payouts = engine.calculate_payouts()
    print("\n--- Epoch Reward Distribution Test ---")
    for peer_id, amount in payouts.items():
        print(f"[{peer_id[:12]}] -> {amount} $DOPA")


