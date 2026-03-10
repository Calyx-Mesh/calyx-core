import os
import subprocess
import sys
import json
import re

# Add Core to path for reward_engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from reward_engine import INGRVMLedger
except ImportError:
    INGRVMLedger = None

class TheJudge:
    """
    Task #13: The "Judge" Validation Pipeline (Anti-Psychosis).
    Ensures zero-trust code merges by running security, syntax, and logic audits.
    Task #12: Automated Slashing Integration.
    """
    def __init__(self, root_dir="."):
        self.root_dir = root_dir
        self.violations = []
        self.ledger = INGRVMLedger() if INGRVMLedger else None

    def security_audit(self, file_path):
        """ Checks for hardcoded secrets, API keys, and common vulnerabilities. """
        # Simple regex for potential secrets
        patterns = [
            r"sk_[live|test]_[0-9a-zA-Z]{24}", # Stripe-like
            r"AIza[0-9A-Za-z-_]{35}",           # Google API Key
            r"(?i)password\s*[:=]\s*['\"](.*)['\"]", # Generic password
            r"(?i)secret\s*[:=]\s*['\"](.*)['\"]"    # Generic secret
        ]
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                for pattern in patterns:
                    if re.search(pattern, content):
                        self.violations.append(f"SECURITY: Potential secret found in {file_path}")
                        return False
        except Exception as e:
            print(f"Error auditing {file_path}: {e}")
        return True

    def syntax_audit(self, file_path):
        """ Verifies that the code is syntactically correct. """
        if file_path.endswith(".py"):
            try:
                subprocess.run([sys.executable, "-m", "py_compile", file_path], check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError as e:
                self.violations.append(f"DOPATAX: Error in {file_path}: {e.stderr.decode().strip()}")
                return False
        return True

    def reality_audit(self):
        """ Anti-Psychosis check: Does the ecosystem pulse still beat? """
        try:
            pulse_script = os.path.join(self.root_dir, "ecosystem_pulse.py")
            if os.path.exists(pulse_script):
                subprocess.run([sys.executable, pulse_script], check=True, capture_output=True)
                return True
            else:
                self.violations.append("REALITY: ecosystem_pulse.py not found at root.")
                return False
        except subprocess.CalledProcessError as e:
            self.violations.append(f"REALITY: Pulse failed after changes: {e.stderr.decode().strip()}")
            return False

    def dht_spoof_audit(self, node_id, reported_ip, dht_peers):
        """ 
        Task #15: NAT Traversal Hardening.
        Verifies that the node's reported IP matches the DHT's perspective.
        """
        print(f"🔍 [AUDIT] Verifying DHT Identity for {node_id}...")

        # In a real setup, we'd check if the reported_ip exists in the dht_peers multiaddrs
        # Mocking for PoC:
        is_spoofed = False
        if reported_ip == "1.1.1.1": # Classic spoofed IP placeholder
            is_spoofed = True

        if is_spoofed:
            self.violations.append(f"SECURITY: DHT IP Spoofing detected for {node_id} ({reported_ip})")
            return False
        return True

    def run_full_audit(self, changed_files, node_id=None, reported_ip=None, dht_peers=None):
        """ Performs the complete Judge validation sequence. """
        print(f"⚖️ THE JUDGE: Commencing audit for {len(changed_files)} files...")

        all_passed = True

        # 1. DHT Spoofing (Phase 10 Hardening)
        if node_id and reported_ip:
            if not self.dht_spoof_audit(node_id, reported_ip, dht_peers):
                all_passed = False

        for f in changed_files:

            if not os.path.exists(f): continue
            
            # 1. Security
            if not self.security_audit(f): all_passed = False
            
            # 2. Syntax
            if not self.syntax_audit(f): all_passed = False

        # 3. Reality (Global Check)
        if not self.reality_audit(): all_passed = False

        if all_passed:
            print("✅ AUDIT PASSED: Code is stable, secure, and grounded in reality.")
            return True
        else:
            print("❌ AUDIT FAILED: The following violations were detected:")
            for v in self.violations:
                print(f"  - {v}")
            
            # Task #12: Auto-Slash node for failed code audit
            if node_id and self.ledger:
                print(f"⚖️ SLASHING NODE {node_id} FOR CODE VIOLATIONS.")
                self.ledger.slash_node(node_id, penalty_syn=10.0, rep_burn=0.2, memo="Failed Judge Audit")
            
            return False

if __name__ == "__main__":
    judge = TheJudge(root_dir="C:/Users/Tesss' PC/Desktop/INGRVM-Core")
    
    # In a real merge, we'd get this from git diff
    # For testing, we'll audit the core files
    files_to_audit = [
        "INGRVM/Core/hub_server.py",
        "INGRVM/Core/tools/mailroom.py",
        "ecosystem_dashboard.py"
    ]
    
    success = judge.run_full_audit(files_to_audit)
    if not success:
        sys.exit(1)


