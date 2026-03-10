import sys
import os
import json
import subprocess
from typing import Dict, List

# Add Core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from reward_engine import INGRVMLedger
from governance_dao import INGRVMDAO
from config import INGRVMConfig

class FinalGroundTruthAudit:
    """
    Task #20: Phase 9 Final Ground-Truth Audit.
    Verifies node readiness for Zero-Trust Mainnet Launch.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.ledger_db = "neuromorphic_env/ledger.db"
        self.dao_db = "neuromorphic_env/governance.db"
        self.results = {}

    def audit_identity(self):
        print("🕵️  Auditing Node Identity (Android Keystore)...")
        try:
            from Mobile.android_keystore import AndroidKeystoreManager
            ks = AndroidKeystoreManager()
            if ks.functional:
                sig = ks.sign_data("AUDIT_PROBE")
                if sig:
                    print("✅ Identity: Android Keystore active and signing.")
                    self.results["identity"] = "PASS"
                else:
                    print("❌ Identity: Signing failed.")
                    self.results["identity"] = "FAIL"
            else:
                print("⚠️  Identity: Keystore system not functional.")
                self.results["identity"] = "WARN"
        except ImportError:
            print("❌ Identity: Keystore module not found.")
            self.results["identity"] = "FAIL"

    def audit_ledger(self):
        print("\n🕵️  Auditing Mesh Ledger...")
        if os.path.exists(self.ledger_db):
            ledger = INGRVMLedger(db_path=self.ledger_db)
            rep = ledger.get_reputation(self.node_id)
            print(f"✅ Ledger: Connection stable. Local Reputation: {rep:.2f}")
            self.results["ledger"] = "PASS"
        else:
            print("❌ Ledger: Database not found.")
            self.results["ledger"] = "FAIL"

    def audit_wallet(self):
        print("\n🕵️  Auditing Mobile Wallet...")
        try:
            from Mobile.mobile_wallet import MobileWallet
            wallet = MobileWallet()
            print(f"✅ Wallet: Address {wallet.data['address']} verified.")
            print(f"💰 Balance: {wallet.data['balance_syn']} $DOPA (Public) | {wallet.data['private_balance']} $DOPA (Private)")
            self.results["wallet"] = "PASS"
        except Exception as e:
            print(f"❌ Wallet error: {e}")
            self.results["wallet"] = "FAIL"

    def audit_p2p(self):
        print("\n🕵️  Auditing P2P Discovery...")
        # Check if we can find the hub
        try:
            from Infrastructure.lan_discovery import discover_hub
            ip, port = discover_hub(timeout=3)
            if ip:
                print(f"✅ P2P: Hub discovered at {ip}:{port}")
                self.results["p2p"] = "PASS"
            else:
                print("⚠️  P2P: Hub not found via mDNS (Check if PC_MASTER is online).")
                self.results["p2p"] = "WARN"
        except ImportError:
            print("❌ P2P: Discovery module not found.")
            self.results["p2p"] = "FAIL"

    def generate_report(self):
        print("\n" + "="*40)
        print("🌍 PHASE 9 GROUND-TRUTH AUDIT REPORT")
        print("="*40)
        for system, status in self.results.items():
            emoji = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
            print(f"{emoji} {system.upper():<10} : {status}")
        
        if all(v == "PASS" for v in self.results.values()):
            print("\n🚀 NODE IS MISSION-READY FOR MAINNET.")
        else:
            print("\n🚧 NODE HAS OUTSTANDING BLOCKS. SEE ABOVE.")
        print("="*40)

if __name__ == "__main__":
    # Ensure we run from root
    if not os.path.exists("neuromorphic_env"):
        print("❌ Error: Run from project root (e.g. 'python INGRVM/Core/tools/final_ground_truth_audit.py')")
        sys.exit(1)
        
    auditor = FinalGroundTruthAudit(os.getenv("INGRVM_NODE_ID", "MOBILE_EDGE"))
    auditor.audit_identity()
    auditor.audit_ledger()
    auditor.audit_wallet()
    auditor.audit_p2p()
    auditor.generate_report()

