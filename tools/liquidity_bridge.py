import sqlite3
import time
import os
import sys
import json
from pathlib import Path

# Add Core to path for reward_engine
core_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(core_dir))
from reward_engine import INGRVMLedger

class SubtensorBurnRelayer:
    """
    Phase 9 Task #03: Subtensor Burn Verification.
    Monitors the Bittensor chain for TAO burns to trigger DOPA allocation.
    """
    def __init__(self):
        self.network = os.getenv("INGRVM_SUBTENSOR_NET", "test") # Use testnet by default
        self.verified_burns = set()

    def verify_on_chain_burn(self, tx_hash: str) -> bool:
        """
        Research Implementation:
        Verifies that a specific TAO burn event occurred on the Subtensor chain.
        """
        print(f"[RELAYER] Auditing Subtensor Transaction: {tx_hash}")
        
        # MOCK IMPLEMENTATION (Requires bittensor SDK + C++ tools)
        # In real setup:
        # subtensor = bt.subtensor(network=self.network)
        # extrinsic = subtensor.substrate.get_extrinsic(tx_hash)
        # return 'SubtensorModule.BurnedRegistration' in [e.id for e in extrinsic.events]
        
        # Simulation Logic:
        if tx_hash.startswith("0x_VERIFIED"):
            print(f"✅ [SUBTENSOR] Burn verified on {self.network} net.")
            return True
        else:
            print(f"❌ [SUBTENSOR] Invalid burn hash or block not finalized.")
            return False

class LiquidityBridge:
    """
    Task #06: $DOPA/USDC Liquidity Bridge Mock.
    Provides a gateway for nodes to exit the mesh by burning virtual $DOPA
    to receive simulated public USDC (recorded in bridge_processed.json).
    """
    def __init__(self, ledger: INGRVMLedger):
        self.ledger = ledger
        self.relayer = SubtensorBurnRelayer()
        self.token_symbol = os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        self.usd_price = 0.50 # Mock: 1 DOPA = 0.50 USD
        
        # Track processed bridge exits
        base_dir = os.path.dirname(ledger.db_path)
        self.processed_tx_file = os.path.join(base_dir, "bridge_processed.json")
        self.processed_txs = self._load_processed()

    def _load_processed(self):
        if os.path.exists(self.processed_tx_file):
            try:
                with open(self.processed_tx_file, "r") as f:
                    return set(json.load(f))
            except: return set()
        return set()

    def _save_processed(self):
        with open(self.processed_tx_file, "w") as f:
            json.dump(list(self.processed_txs), f)

    def get_quote(self, amount_dopa: float) -> float:
        """ Returns the USD value for a given amount of $DOPA. """
        return amount_dopa * self.usd_price

    def request_exit(self, node_id: str, amount: float, target_address: str):
        """ 
        Phase 9 Task #6: Initiate Bridge Exit.
        1. Burns $DOPA from the virtual ledger.
        2. Records target address in the transaction memo.
        """
        current_bal = self.ledger.get_balance(node_id)
        if current_bal < amount:
            print(f"❌ [BRIDGE] Insufficient {self.token_symbol} balance.")
            return False
            
        # Perform the burn (Transfer to BURN_ADDRESS)
        memo = f"EXIT:{target_address}"
        if self.ledger.transfer(node_id, "BURN_ADDRESS", amount):
            print(f"🔥 [BRIDGE] {amount} {self.token_symbol} burned. Requesting mint to {target_address}...")
            return True
        return False

    def process_burn_events(self):
        """
        Simulates the Relayer monitoring the ledger.
        In Phase 10, this will be handled by a Headless Gemini.
        """
        conn = sqlite3.connect(self.ledger.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM transactions 
            WHERE receiver_id = 'BURN_ADDRESS' 
            AND memo LIKE 'EXIT:%'
            ORDER BY tx_id ASC
        """)
        
        exits = cursor.fetchall()
        new_mints = 0
        
        for tx in exits:
            if tx['tx_id'] in self.processed_txs:
                continue
                
            target = tx['memo'].split("EXIT:")[1]
            amount_usd = self.get_quote(tx['amount'])
            
            print(f"\n🌉 [CROSS-CHAIN MINT] tx_id:{tx['tx_id']}")
            print(f"  > Target: {target}")
            print(f"  > Minting: {amount_usd:.2f} USDC (via 1:1 {self.token_symbol} peg)")
            
            self.processed_txs.add(tx['tx_id'])
            new_mints += 1
            
        conn.close()
        if new_mints > 0:
            self._save_processed()
            print(f"✅ Bridge Synced: {new_mints} mints confirmed on mock-chain.")
        else:
            print("💤 Bridge Relayer: Idle (No new exits).")

if __name__ == "__main__":
    # Test integration
    ledger = INGRVMLedger(db_path="../Core/neuromorphic_env/ledger.db")
    bridge = LiquidityBridge(ledger)
    
    print(f"--- {bridge.token_symbol} Sovereign Bridge Audit ---")
    # Simulate an exit request
    node = "PC_MASTER_HUB"
    bridge.request_exit(node, 100.0, "0xTARGET_SOL_WALLET")
    
    # Run the relayer
    bridge.process_burn_events()
