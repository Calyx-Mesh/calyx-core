import sqlite3
import os
import time
import json
from typing import Optional, Dict, Any

class ShardCache:
    """
    Phase 10 Task #10: Persistent Shards.
    Caches sharded model weights in a local SQLite database for instant restart.
    """
    def __init__(self, db_path: str = "neuromorphic_env/shard_cache.db"):
        self.db_path = db_path
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shard_weights (
                shard_id TEXT PRIMARY KEY,
                model_name TEXT,
                layer_start INTEGER,
                layer_end INTEGER,
                weights BLOB,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save_shard(self, model_name: str, layer_start: int, layer_end: int, weights: bytes, metadata: Dict = None):
        """ Stores shard weights in the persistent local cache. """
        shard_id = f"{model_name}_{layer_start}_{layer_end}"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        meta_json = json.dumps(metadata) if metadata else "{}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO shard_weights (shard_id, model_name, layer_start, layer_end, weights, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (shard_id, model_name, layer_start, layer_end, weights, meta_json))
        
        conn.commit()
        conn.close()
        print(f"[CACHE] Persistent Shard Saved: {shard_id}")

    def load_shard(self, model_name: str, layer_start: int, layer_end: int) -> Optional[bytes]:
        """ Retrieves shard weights from the cache. """
        shard_id = f"{model_name}_{layer_start}_{layer_end}"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT weights FROM shard_weights WHERE shard_id = ?", (shard_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[CACHE] Persistent Shard Loaded: {shard_id}")
            return row[0]
        return None

    def clear_cache(self):
        """ Purges all cached shards. """
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            self._init_db()
            print("[CACHE] Persistent Shard Cache cleared.")

# --- Module Test ---
if __name__ == "__main__":
    cache = ShardCache()
    
    mock_weights = b"fake_weights_010101"
    cache.save_shard("Llama-3-Mock", 6, 25, mock_weights)
    
    loaded = cache.load_shard("Llama-3-Mock", 6, 25)
    if loaded == mock_weights:
        print("✅ SUCCESS: Shard persistence verified.")
    else:
        print("❌ FAILED: Persistence error.")
