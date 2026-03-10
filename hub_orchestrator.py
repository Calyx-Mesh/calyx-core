import time
import json
import os
from typing import Dict, List, Optional
from shard_manager import ShardManager

class RuleZeroValidator:
    """
    The 'Rule Zero' Validator (Task #07).
    Forces cross-node sync by validating that every peer's 
    'last_seen' heartbeat is within a strict threshold (e.g. < 5 mins).
    """
    def __init__(self, shard_mgr: ShardManager, sync_threshold_sec: int = 300):
        self.shard_mgr = shard_mgr
        self.sync_threshold = sync_threshold_sec
        self.denied_nodes: List[str] = []

    def validate_mesh(self) -> Dict[str, bool]:
        """
        Checks all discovered nodes against the Rule Zero threshold.
        Returns a mapping of node_id -> is_synced.
        """
        results = {}
        current_time = time.time()
        
        # We need to peek into shard_mgr's discovery_dir or its internal mesh_shards
        # Since shard_manager.py's mesh_shards stores lists of Shards, we'll check the source files.
        discovery_dir = self.shard_mgr.discovery_dir
        
        if not os.path.exists(discovery_dir):
            return {}

        for filename in os.listdir(discovery_dir):
            if filename.endswith(".json") and not filename.startswith(self.shard_mgr.node_id):
                path = os.path.join(discovery_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        node_id = data.get("node_id", "UNKNOWN")
                        last_seen = data.get("last_seen", 0)
                        
                        # Rule Zero: Node MUST have heartbeat within the threshold
                        is_synced = (current_time - last_seen) <= self.sync_threshold
                        results[node_id] = is_synced
                        
                        if not is_synced:
                            print(f"[RULE-ZERO] Node {node_id} is OUT OF DOPAC. Participation denied.")
                        else:
                            print(f"[RULE-ZERO] Node {node_id} verified. Participation granted.")
                except Exception as e:
                    print(f"[ERROR] Rule Zero validation failed for {filename}: {e}")
        
        return results

    def get_authorized_shards(self) -> Dict[str, List]:
        """
        Filters the shard manager's mesh_shards to only include synced nodes.
        """
        sync_status = self.validate_mesh()
        authorized = {}
        
        for node_id, shards in self.shard_mgr.mesh_shards.items():
            if sync_status.get(node_id, False):
                authorized[node_id] = shards
        
        return authorized

if __name__ == "__main__":
    # Simple test run
    sm = ShardManager("HUB_ORCHESTRATOR", discovery_dir="mesh_discovery")
    validator = RuleZeroValidator(sm)
    status = validator.validate_mesh()
    print(f"Mesh Sync Status: {status}")

