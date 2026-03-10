import json
import os
import hashlib
import msgpack
import torch
import io
import sys
import argparse
import requests
from typing import Dict, Optional
from packaging import version
from dotenv import load_dotenv

# Load environment variables for Hub URL
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

HUB_URL = os.getenv("INGRVM_HUB_URL", "http://127.0.0.1:8000")

class INGRVMPackager:
    """
    Phase 6: Bundles SNN weights, architecture metadata, and semantic versioning
    into a single '.ingrvm' binary file for mesh distribution.
    """
    def __init__(self):
        pass

    def create_package(self, ingrvm_id: str, weights_path: str, meta: Dict, output_dir: str) -> str:
        """
        Creates a .ingrvm package with semantic version validation.
        """
        # Validate Semantic Versioning (Task #9)
        v_str = meta.get("version", "0.0.1")
        try:
            version.parse(v_str)
        except version.InvalidVersion:
            print(f"❌ ERROR: Invalid semantic version: {v_str}")
            sys.exit(1)

        print(f"[PACKAGER] Creating .ingrvm package: {ingrvm_id} v{v_str}")
        
        # 1. Load weights
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Weights file not found: {weights_path}")
            
        with open(weights_path, "rb") as f:
            weights_bytes = f.read()
            
        # 2. Calculate Integrity Hash
        integrity_hash = hashlib.sha256(weights_bytes).hexdigest()
        meta["integrity_hash"] = integrity_hash
        meta["ingrvm_id"] = ingrvm_id
        
        # 3. Bundle with MessagePack
        package_data = {
            "ingrvm_id": ingrvm_id,
            "version": v_str,
            "metadata": meta,
            "weights": weights_bytes
        }
        
        binary_package = msgpack.packb(package_data, use_bin_type=True)
        
        # 4. Write to disk
        filename = f"{ingrvm_id}_{v_str}.ingrvm"
        output_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_path, "wb") as f:
            f.write(binary_package)
            
        print(f"✅ SUCCESS: {output_path} generated ({len(binary_package)} bytes)")
        return output_path

    def upload_to_marketplace(self, package_path: str):
        """
        Uploads the finished package to the PC Master Hub.
        """
        print(f"[PACKAGER] Uploading {package_path} to Marketplace at {HUB_URL}...")
        
        # We need to unpack briefly to get the metadata for the API params
        with open(package_path, "rb") as f:
            data = msgpack.unpackb(f.read(), raw=False)
        
        meta = data["metadata"]
        params = {
            "name": meta.get("name", data["ingrvm_id"]),
            "author_id": meta.get("author_id", "ANON"),
            "version": data["version"],
            "category": meta.get("category", "General"),
            "description": meta.get("description", ""),
            "architecture": meta.get("architecture", "SNN")
        }
        
        url = f"{HUB_URL}/api/marketplace/upload"
        try:
            with open(package_path, "rb") as f:
                files = {"file": (os.path.basename(package_path), f, "application/octet-stream")}
                response = requests.post(url, params=params, files=files)
            
            if response.status_code == 200:
                print(f"🚀 MARKETPLACE UPLOAD SUCCESS: {response.json()}")
            else:
                print(f"❌ UPLOAD FAILED: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ UPLOAD ERROR: {e}")

def main():
    parser = argparse.ArgumentParser(description="INGRVM INGRVM Packager CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Create command
    create_p = subparsers.add_parser("create", help="Bundle weights into a .ingrvm file")
    create_p.add_argument("--id", required=True, help="INGRVM ID (e.g. sentiment_alpha)")
    create_p.add_argument("--weights", required=True, help="Path to .pt weights file")
    create_p.add_argument("--ver", default="0.1.0", help="Semantic version (e.g. 1.2.3)")
    create_p.add_argument("--name", help="Display name")
    create_p.add_argument("--author", default="LAPTOP_RELAY", help="Author ID")
    create_p.add_argument("--out", default="neuromorphic_env/packages", help="Output directory")
    create_p.add_argument("--upload", action="store_true", help="Upload to Hub after creation")

    args = parser.parse_args()

    packager = INGRVMPackager()

    if args.command == "create":
        meta = {
            "name": args.name if args.name else args.id,
            "author_id": args.author,
            "version": args.ver,
            "category": "Community",
            "description": f"Packaged via CLI: {args.id}",
            "architecture": "BitNet-1bit"
        }
        pkg_path = packager.create_package(args.id, args.weights, meta, args.out)
        
        if args.upload:
            packager.upload_to_marketplace(pkg_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

