import time
import os
import requests
import numpy as np
from typing import Dict, List
from peer_database import PeerDatabase
from reward_engine import RewardEngine

class SubtensorBridge:
    """
    Task #06: Subtensor Sovereign Bridge.
    Connects the INGRVM Mesh to the Bittensor ecosystem ($DOPA <-> $TAO).
    Fetches market data to determine emission value.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db
        self.epoch_num = 0
        self.tao_usd_price = 0.0
        self.token_symbol = os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        self.syn_tao_rate = 0.001 # Initial peg: 1000 tokens per 1 TAO

    def fetch_market_state(self):
        """ Task #06: Fetches real TAO price from CoinGecko. """
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bittensor&vs_currencies=usd"
            resp = requests.get(url, timeout=5).json()
            self.tao_usd_price = resp['bittensor']['usd']
            print(f"[BRIDGE] Live TAO Price: ${self.tao_usd_price}")
        except Exception as e:
            print(f"[BRIDGE] Market fetch failed, using fallback. Error: {e}")
            self.tao_usd_price = 450.0 # Fallback

    def run_epoch(self, active_work: Dict[str, int]):
        """
        Settles mesh activity based on Bittensor-linked tokenomics.
        """
        self.fetch_market_state()
        self.epoch_num += 1
        
        # Emission scales with TAO value to maintain node profitability
        emission = 500.0 * (self.tao_usd_price / 400.0) 
        print(f"\n--- BITTENSOR EPOCH #{self.epoch_num} | Emission: {emission:.2f} ${self.token_symbol} ---")
        
        engine = RewardEngine(epoch_emission=emission)
        
        for peer_id, spikes in active_work.items():
            record = self.db.get_peer(peer_id)
            rep = record.reputation if record else 1.0
            engine.register_work(peer_id, spikes)
            if peer_id in engine.nodes:
                engine.nodes[peer_id].reputation_score = rep

        payouts = engine.calculate_payouts()
        
        print(f"[SUBTENSOR] Committing settlement to peer DB...")
        for peer_id, amount in payouts.items():
            self.db.update_peer(peer_id, spikes=0, reward=amount)
            print(f"  > Node {peer_id[:8]} | +{amount:.4f} ${self.token_symbol} (Value: ~{amount * self.syn_tao_rate:.6f} TAO)")

        print(f"--- EPOCH #{self.epoch_num} FINALIZED ---")

# --- Verification Test ---
if __name__ == "__main__":
    database = PeerDatabase()
    blockchain = SubtensorBridge(database)
    
    # Mock data from the mesh during this epoch
    mock_mesh_work = {
        "12D3KooW_PC_BACKBONE": 8500,
        "12D3KooW_PIXEL_8": 2100,
        "12D3KooW_MOCK_PEER_ALPHA": 450
    }
    
    # Run two epochs to see accumulation
    blockchain.run_epoch(mock_mesh_work)
    time.sleep(1)
    
    # Simulate node alpha doing more work in second epoch
    mock_mesh_work["12D3KooW_MOCK_PEER_ALPHA"] = 3000
    blockchain.run_epoch(mock_mesh_work)
    
    if database.get_peer("12D3KooW_MOCK_PEER_ALPHA").tokens_earned > 0:
        print("\nSUCCESS: Bittensor Sovereign Bridge is functional.")


