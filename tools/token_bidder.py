import random
import time
from typing import List, Dict

class TokenBidder:
    """
    Economy Engine: Nodes 'Bid' to process high-value Neural Shards.
    The mesh chooses the node with the best Reputation/Price ratio.
    """
    def __init__(self, node_id: str, current_reputation: float):
        self.node_id = node_id
        self.reputation = current_reputation

    def submit_bid(self, shard_id: str, base_reward: float) -> Dict:
        """
        Submits a competitive bid for a task.
        Logic: A node with higher reputation can 'bid' lower to win the slot.
        """
        # Bid price is based on reputation. 
        # Higher reputation nodes can afford lower bids because they are trusted.
        bid_price = base_reward * (1.5 - (self.reputation / 2.0))
        
        bid = {
            "node_id": self.node_id,
            "shard_id": shard_id,
            "bid_price": round(bid_price, 4),
            "reputation": self.reputation,
            "timestamp": time.time()
        }
        print(f"[BID] Node {self.node_id[:8]} bidding {bid_price:.4f} $DOPA for {shard_id}")
        return bid

    def resolve_auction(self, bids: List[Dict]) -> Dict:
        """
        The Mesh selects the winning bidder.
        Criteria: Best value (Lowest price * Highest reputation factor).
        """
        scored_bids = []
        for b in bids:
            # Score = BidPrice / Reputation (Lower is better for the network)
            score = b['bid_price'] / b['reputation']
            scored_bids.append({**b, "score": score})
        
        scored_bids.sort(key=lambda x: x['score'])
        winner = scored_bids[0]
        print(f"\n[AUCTION] Winner: {winner['node_id'][:8]} | Score: {winner['score']:.4f}")
        return winner

# --- Verification Test ---
if __name__ == "__main__":
    # Simulate an auction for an 80B Model Layer Shard
    auctioneer = TokenBidder("NETWORK_ORCHESTRATOR", 2.0)
    
    bidder_a = TokenBidder("12D3_TIER_1_PC", 1.9)
    bidder_b = TokenBidder("12D3_OLD_LAPTOP", 0.8)
    
    bids = [
        bidder_a.submit_bid("Llama3_Layer_10", 10.0),
        bidder_b.submit_bid("Llama3_Layer_10", 10.0)
    ]
    
    winner = auctioneer.resolve_auction(bids)
    
    if winner['node_id'] == "12D3_TIER_1_PC":
        print("\nSUCCESS: Token Bidding logic correctly prioritized high-trust hardware.")

