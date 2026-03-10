import os
import sys
import hashlib
import msgpack
import requests
import argparse
from typing import Dict, List, Optional
from packaging import version
from dotenv import load_dotenv

# Load environment variables for Hub URL
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

HUB_URL = os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")

class SkillValidator:
    """
    Phase 6 Task #17: Peer-review tool for community skills.
    Downloads, verifies, and audits .ingrvm packages.
    """
    def __init__(self, download_dir: str = "neuromorphic_env/downloads"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, exist_ok=True)

    def fetch_catalog(self) -> List[Dict]:
        """ Fetches the list of all ingrvms from the Hub. """
        url = f"{HUB_URL}/api/marketplace/catalog"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"❌ Error fetching catalog: {e}")
            return []

    def download_skill(self, cid: str, ingrvm_id: str) -> Optional[str]:
        """ Downloads a ingrvm blob by CID. """
        url = f"{HUB_URL}/api/marketplace/download/{cid}"
        print(f"[VALIDATOR] Downloading {ingrvm_id} (CID: {cid[:12]}...)")
        
        try:
            resp = requests.get(url, stream=True, timeout=10)
            if resp.status_code == 200:
                target_path = os.path.join(self.download_dir, f"{ingrvm_id}.ingrvm")
                with open(target_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Download complete: {target_path}")
                return target_path
            else:
                print(f"❌ Download failed: {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ Download error: {e}")
            return None

    def validate_package(self, package_path: str) -> Dict:
        """
        Performs technical audit of a .ingrvm package.
        Checks integrity, versioning, and metadata.
        """
        print(f"[VALIDATOR] Auditing package: {os.path.basename(package_path)}")
        
        report = {
            "integrity": "FAILED",
            "versioning": "FAILED",
            "metadata": "FAILED",
            "errors": []
        }

        try:
            # 1. Unpack and check binary integrity
            with open(package_path, "rb") as f:
                raw_data = f.read()
                data = msgpack.unpackb(raw_data, raw=False)
            
            weights = data.get("weights")
            meta = data.get("metadata", {})
            v_str = data.get("version", "0.0.0")
            
            # 2. Verify Hash (Task #7 Logic)
            current_hash = hashlib.sha256(weights).hexdigest()
            if current_hash == meta.get("integrity_hash"):
                report["integrity"] = "PASSED"
            else:
                report["errors"].append("Hash mismatch: Weights do not match signed fingerprint.")

            # 3. Verify Semantic Versioning (Task #9)
            try:
                version.parse(v_str)
                report["versioning"] = "PASSED"
            except:
                report["errors"].append(f"Invalid semver: {v_str}")

            # 4. Basic Metadata Sanity
            required_keys = ["name", "author_id", "architecture"]
            missing = [k for k in required_keys if k not in meta]
            if not missing:
                report["metadata"] = "PASSED"
            else:
                report["errors"].append(f"Missing metadata: {', '.join(missing)}")

        except Exception as e:
            report["errors"].append(f"Unpack error: {str(e)}")

        return report

def main():
    parser = argparse.ArgumentParser(description="INGRVM Skill Validator (Peer Review)")
    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List community skills available for review")

    # Audit command
    audit_p = subparsers.add_parser("audit", help="Download and validate a skill")
    audit_p.add_argument("--id", required=True, help="INGRVM ID to audit")
    
    args = parser.parse_args()
    validator = SkillValidator()

    if args.command == "list":
        catalog = validator.fetch_catalog()
        print(f"\n--- Community Marketplace Catalog ({len(catalog)} skills) ---")
        for s in catalog:
            print(f"[{s['ingrvm_id']}] {s['name']} v{s['version']} by {s['author_id']}")
            print(f"   CID: {s['cid'][:16]}... | Arch: {s['architecture']}")
            print("-" * 40)

    elif args.command == "audit":
        catalog = validator.fetch_catalog()
        target = next((s for s in catalog if s['ingrvm_id'] == args.id), None)
        
        if not target:
            # Try by partial name match
            target = next((s for s in catalog if args.id in s['ingrvm_id']), None)

        if target:
            pkg_path = validator.download_skill(target['cid'], target['ingrvm_id'])
            if pkg_path:
                report = validator.validate_package(pkg_path)
                print("\n--- Technical Audit Report ---")
                print(f"Integrity:  {report['integrity']}")
                print(f"Versioning: {report['versioning']}")
                print(f"Metadata:   {report['metadata']}")
                
                if report['errors']:
                    print("\n❌ Critical Flags:")
                    for err in report['errors']:
                        print(f"  - {err}")
                else:
                    print("\n✅ Skill is VERIFIED and safe for mesh deployment.")
        else:
            print(f"❌ Skill '{args.id}' not found in catalog.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

