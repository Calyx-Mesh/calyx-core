import time
import requests
import json
import os
import sys
from dotenv import load_dotenv

# Import the new INGRVM SDK (Phase 7 Task #16)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(base_dir, 'Framework'))
try:
    from sdk import INGRVMSDK
except ImportError:
    print(f"❌ ERROR: INGRVM SDK not found at {os.path.join(base_dir, 'Framework')}. Please ensure INGRVM/Framework/sdk.py exists.")
    sys.exit(1)

# Load env for Hub URL
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)
HUB_URL = os.getenv("INGRVM_HUB_URL", "http://192.168.68.51:8000")

def run_paid_inference_test():
    """
    Phase 6 Task #19: System Test (Paid Inference).
    1. Check initial balance.
    2. Execute multiple inferences.
    3. Verify rewards are minted/distributed in the SQL Ledger.
    """
    client_id = "USER_NODE_TEST"
    sdk = INGRVMSDK(hub_url=HUB_URL, peer_id=client_id)
    
    print(f"--- [PHASE 6] PAID INFERENCE SYSTEM TEST ---")
    print(f"Target Hub: {HUB_URL}")
    print(f"User Identity: {client_id}\n")

    # 1. Initial Balance
    initial_balance = sdk.get_balance()
    print(f"[PRE-TEST] Initial Balance: {initial_balance:.4f} $DOPA")

    # 2. Execute Spikes
    test_prompts = [
        "The neural fabric is expanding rapidly.",
        "Solarpunk architecture is the future of the mesh.",
        "Decentralized intelligence is sovereign.",
        "The Pixel 8 is a powerful edge node.",
        "INGRVM is the nervous system of the ecosystem."
    ]

    print(f"\n[ACT] Firing {len(test_prompts)} neural pulses...")
    for i, prompt in enumerate(test_prompts):
        print(f"  Pulse {i+1}: '{prompt}'")
        res = sdk.send_spike(prompt)
        if res.get("status") == "QUEUED":
            print(f"    ✅ Success: Spike queued (Depth: {res.get('queue_depth', 0)})")
        else:
            print(f"    ❌ Failed: {res}")
        time.sleep(1) # Give the Hub's neural_worker time to process

    # 3. Verification
    print(f"\n[WAIT] Waiting for asynchronous reward settlement...")
    time.sleep(5)

    final_balance = sdk.get_balance()
    diff = final_balance - initial_balance
    
    print(f"\n[POST-TEST] Final Balance: {final_balance:.4f} $DOPA")
    print(f"[RESULTS] Total $DOPA Minted: +{diff:.4f}")

    if diff > 0:
        print(f"✅ SUCCESS: The 'Paid' Inference loop is functional and persistent.")
        print(f"Check the Dashboard 'Ledger' tab to see the transaction history.")
    else:
        print(f"⚠️ WARNING: Balance did not increase. Check hub_server.py logs.")

    # 4. Check Ledger
    ledger = sdk.get_ledger()
    print(f"\n--- Recent Transaction History ---")
    for tx in ledger[:5]:
        print(f"[{tx['tx_type']}] {tx['amount']:+.4f} $DOPA | {tx['memo']}")

if __name__ == "__main__":
    run_paid_inference_test()


