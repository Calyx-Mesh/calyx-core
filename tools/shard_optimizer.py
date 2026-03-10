import os
import time
import shutil

class ShardOptimizer:
    """
    INGRVM Shard Optimizer: Prunes old or unused neural shards to free up VRAM and Disk space.
    Essential for long-running Phase 2 Muscle tasks.
    """
    def __init__(self, shard_dir="ingrvms", max_shards=10):
        self.shard_dir = shard_dir
        self.max_shards = max_shards
        os.makedirs(shard_dir, exist_ok=True)

    def migrate_legacy_weights(self, legacy_dir="../../../neuromorphic_env/ingrvms"):
        """
        Task #06: Migrates weights from the old environment to the new INGRVM structure.
        """
        if not os.path.exists(legacy_dir):
            return

        print(f"📦 --- Weight Migration: {legacy_dir} -> {self.shard_dir} ---")
        legacy_files = [f for f in os.listdir(legacy_dir) if f.endswith(('.pt', '.json'))]
        
        for f in legacy_files:
            src = os.path.join(legacy_dir, f)
            dst = os.path.join(self.shard_dir, f)
            if not os.path.exists(dst):
                shutil.move(src, dst)
                print(f"✅ Migrated: {f}")
            else:
                os.remove(src) # Cleanup if already exists in new home
                print(f"🗑️ Cleaned legacy: {f}")

    def optimize(self):
        """
        Scans for neural shards and keeps only the most recent ones.
        """
        # First, ensure migration is done
        self.migrate_legacy_weights()
        
        print(f"🧹 --- Shard Optimizer: {self.shard_dir} ---")
        
        # 1. Get all shard files (.pt and .json)
        shards = [f for f in os.listdir(self.shard_dir) if f.endswith(('.pt', '.json'))]
        
        if not shards:
            print("✅ No shards found to optimize.")
            return

        # 2. Sort by modification time (oldest first)
        shards_with_time = []
        for s in shards:
            path = os.path.join(self.shard_dir, s)
            shards_with_time.append((path, os.path.getmtime(path)))
            
        shards_with_time.sort(key=lambda x: x[1])
        
        # 3. Prune if over max_shards
        if len(shards_with_time) > self.max_shards:
            num_to_delete = len(shards_with_time) - self.max_shards
            print(f"⚠️ Found {len(shards_with_time)} shards. Pruning {num_to_delete} oldest...")
            
            for i in range(num_to_delete):
                path, _ = shards_with_time[i]
                try:
                    os.remove(path)
                    print(f"❌ Deleted: {os.path.basename(path)}")
                except Exception as e:
                    print(f"⚠️ Failed to delete {path}: {e}")
        else:
            print(f"✅ Shard count within limit ({len(shards_with_time)}/{self.max_shards}).")

if __name__ == "__main__":
    opt = ShardOptimizer()
    opt.optimize()

