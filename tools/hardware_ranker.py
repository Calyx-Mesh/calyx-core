import psutil
import torch
import os
import json
from typing import Dict, Any

class HardwareRanker:
    """
    Phase 10 Task #14: Hardware Tier Ranking.
    Assigns a node tier (1-4) based on local compute capabilities.
    Directly impacts Swarm Bidding power in the Cortex Bus.
    """
    def __init__(self):
        self.stats = self._get_raw_stats()
        self.tier, self.multiplier = self._calculate_tier()

    def _get_raw_stats(self) -> Dict[str, Any]:
        """ Collects local hardware metrics. """
        stats = {
            "cpu_count": psutil.cpu_count(logical=True),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "vram_total_gb": 0.0,
            "has_cuda": torch.cuda.is_available()
        }
        
        if stats["has_cuda"]:
            stats["vram_total_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            
        return stats

    def _calculate_tier(self) -> (int, float):
        """
        Ranking Logic:
        - Tier 1 (Elite): 16+ Cores OR 12GB+ VRAM (Multiplier: 2.0)
        - Tier 2 (Pro): 8+ Cores OR 6GB+ VRAM (Multiplier: 1.5)
        - Tier 3 (Standard): 4+ Cores AND 8GB+ RAM (Multiplier: 1.0)
        - Tier 4 (Legacy): All others (Multiplier: 0.5)
        """
        s = self.stats
        
        if s["cpu_count"] >= 16 or s["vram_total_gb"] >= 12.0:
            return 1, 2.0
        elif s["cpu_count"] >= 8 or s["vram_total_gb"] >= 6.0:
            return 2, 1.5
        elif s["cpu_count"] >= 4 and s["ram_total_gb"] >= 8.0:
            return 3, 1.0
        else:
            return 4, 0.5

    def get_rank_report(self) -> Dict[str, Any]:
        return {
            "node_id": os.getenv("INGRVM_NODE_ID", "UNKNOWN"),
            "tier": self.tier,
            "bid_multiplier": self.multiplier,
            "hardware": self.stats
        }

    def save_rank(self, path: str = "neuromorphic_env/hardware_tier.json"):
        report = self.get_rank_report()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=4)
        print(f"[RANKER] Hardware Ranked: TIER {self.tier} (Multiplier: {self.multiplier}x)")

if __name__ == "__main__":
    ranker = HardwareRanker()
    report = ranker.get_rank_report()
    
    print("\n--- 🛡️ INGRVM Hardware Tier Report ---")
    print(f"Tier:       {report['tier']}")
    print(f"Bidding Multiplier: {report['bid_multiplier']}x")
    print(f"CPU Cores:  {report['hardware']['cpu_count']}")
    print(f"RAM:        {report['hardware']['ram_total_gb']} GB")
    print(f"VRAM:       {report['hardware']['vram_total_gb']} GB (CUDA: {report['hardware']['has_cuda']})")
    print("--------------------------------------\n")
    
    ranker.save_rank()
