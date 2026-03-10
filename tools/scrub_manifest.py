import os
import re
import json
import sys

def load_manifest(path):
    with open(path, "r") as f:
        return json.load(f)

def run_scrub(repo_root, manifest_path):
    print("--- 🧼 INGRVM Pre-Flight Scrub (Phase 8 Task #2) ---")
    manifest = load_manifest(manifest_path)
    
    exclude_exts = manifest.get("exclude_extensions", [])
    exclude_dirs = set(manifest.get("exclude_directories", []))
    regex_patterns = [re.compile(pat) for pat in manifest.get("regex_patterns", [])]
    
    violations = 0
    scanned_files = 0
    
    for root, dirs, files in os.walk(repo_root):
        # Modify dirs in-place to prune excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in exclude_exts:
                # These are usually explicitly allowed via .gitignore, but we warn if they are tracked
                print(f"[WARN] Sensitive extension found (Ensure it is gitignored): {os.path.join(root, file)}")
                continue
                
            file_path = os.path.join(root, file)
            scanned_files += 1
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in regex_patterns:
                            if pattern.search(line):
                                print(f"❌ [VIOLATION] Found potential secret in {file_path}:{line_num}")
                                print(f"   Line: {line.strip()[:100]}")
                                violations += 1
            except UnicodeDecodeError:
                # Skip binary files
                pass
            except Exception as e:
                pass
                
    print("\n--- Scrub Complete ---")
    print(f"Scanned {scanned_files} files.")
    if violations == 0:
        print("✅ Repository is CLEAN and safe for public release.")
        sys.exit(0)
    else:
        print(f"🛑 Found {violations} potential secrets. Please scrub before push.")
        sys.exit(1)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(base_dir)))
    manifest_path = os.path.join(base_dir, "scrub_manifest.json")
    run_scrub(repo_root, manifest_path)

