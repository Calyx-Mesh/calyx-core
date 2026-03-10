import time
import random

class MercenaryLogger:
    """
    Narrates node activity into the 'Cynical Engineer / Architect' persona.
    Used for YouTube dev-log generation and content strategy.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.cynical_remarks = [
            "Another day, another stack of spikes. The mesh never sleeps, unfortunately.",
            "Consensus reached. At least some parts of this network are thinking straight.",
            "Metabolic limits hit. Even silicon needs a breather when it's carryng the global brain.",
            "Reward settled. Barely enough to cover the electricity, but sovereignty isn't free.",
            "Homeostasis adjusted the threshold. The brain is getting picky. Good.",
            "zkML proof generated. Privacy is a lie, but at least we're making it expensive to break.",
            "Shard registered. Hosting a slice of Llama-3 because the cloud is too bloated to care."
        ]

    def log_event(self, event_type: str, data: dict):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        remark = random.choice(self.cynical_remarks)
        
        print(f"\n[{timestamp}] [THE_ARCHITECT_LOG]")
        print(f"EVENT: {event_type.upper()}")
        print(f"PAYLOAD: {data}")
        print(f"PERSONA: '{remark}'")

# --- Verification Test ---
if __name__ == "__main__":
    logger = MercenaryLogger("4QbWtbA6...")
    
    # 1. Log a Reward Event
    logger.log_event("REWARD_SETTLEMENT", {"amount": "12.5 $DOPA", "epoch": 42})
    
    # 2. Log a Homeostasis Event
    logger.log_event("HOMEOSTASIS_ADJUST", {"new_threshold": 1.75, "reason": "Over-stimulation"})
    
    # 3. Log a Proof Event
    logger.log_event("ZK_PROOF_GEN", {"trace_id": "ddb2e44d...", "status": "COMMITTED"})
    
    print("\nSUCCESS: Mercenary Logger is ready for content generation.")

