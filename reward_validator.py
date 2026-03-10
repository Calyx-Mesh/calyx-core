from identity_manager import NodeIdentity
from spike_protocol import NeuralSpike
from typing import Tuple

class RewardValidator:
    """
    The 'Ticket Inspector' of the INGRVM Mesh.
    Ensures every spike processed by the node is cryptographically signed
    and attributed to a valid peer before it counts as 'Useful Work'.
    """
    def __init__(self):
        print("[VALIDATOR] Reward Integrity System initialized.")

    def verify_spike_integrity(self, spike: NeuralSpike) -> Tuple[bool, str]:
        """
        Verifies the signature of a spike against its node_id (Public Key).
        """
        if not spike.signature:
            return False, "MISSING_SIGNATURE"

        # 1. Capture the signature
        sig_to_verify = spike.signature
        
        # 2. Reset signature field to None to regenerate the exact binary 
        # that was originally signed.
        spike.signature = None
        payload = spike.to_bin()
        
        # 3. Verify using the static Ed25519 helper
        is_valid = NodeIdentity.verify_signature(
            public_key_b64=spike.node_id,
            data=payload,
            signature_b64=sig_to_verify
        )
        
        # 4. Restore the signature for further routing
        spike.signature = sig_to_verify
        
        if is_valid:
            return True, "VERIFIED"
        else:
            return False, "INVALID_SIGNATURE"

# --- Local Verification Test ---
if __name__ == "__main__":
    validator = RewardValidator()
    
    # 1. Create an identity for a 'Peer Node'
    mock_peer_id = NodeIdentity(key_path="neuromorphic_env/temp_peer.key")
    peer_pub_key = mock_peer_id.get_public_key_b64()
    
    # 2. Peer generates a spike
    spike = NeuralSpike(
        task_id="WORK_001",
        ingrvm_id="ingrvm_0",
        node_id=peer_pub_key,
        input_hash="hash_data"
    )
    spike.set_spikes([1, 0, 1])
    
    # 3. Peer signs the spike
    spike.signature = None
    spike.signature = mock_peer_id.sign_data(spike.to_bin())
    
    # 4. Validator checks the spike
    ok, status = validator.verify_spike_integrity(spike)
    print(f"Test Signed Spike: {status} ({ok})")
    
    # 5. Tamper Test
    spike.task_id = "TAMPERED_TASK"
    ok_tamper, status_tamper = validator.verify_spike_integrity(spike)
    print(f"Test Tampered Spike: {status_tamper} (Valid: {ok_tamper})")
    
    if ok and not ok_tamper:
        print("\nSUCCESS: Reward Validator is secure and detects tampering.")
    
    # Cleanup temp key
    import os
    if os.path.exists("neuromorphic_env/temp_peer.key"):
        os.remove("neuromorphic_env/temp_peer.key")
