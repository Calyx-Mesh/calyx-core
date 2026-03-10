from identity_manager import NodeIdentity
from peer_database import PeerDatabase
from spike_protocol import NeuralSpike
from typing import Tuple

class SecurityGateway:
    """
    The Zero-Trust Firewall for your Brain.
    Rejects any traffic that isn't signed by a verified node in the PeerDB.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db

    def verify_ingress(self, spike: NeuralSpike) -> Tuple[bool, str]:
        """
        Checks the 'ID Badge' of the incoming spike.
        """
        peer_id = spike.node_id
        record = self.db.get_peer(peer_id)
        
        # 1. Reputation Check
        if not record or record.reputation < 0.5:
            return False, "DENIED: Peer unknown or untrusted."

        # 2. Signature Check
        if not spike.signature:
            return False, "DENIED: Missing cryptographic signature."

        # To verify, we must remove the signature field before hashing the payload
        # just like we did during the signing process.
        sig_to_verify = spike.signature
        spike.signature = None
        payload_to_verify = spike.to_bin()
        
        is_valid = NodeIdentity.verify_signature(
            public_key_b64=peer_id, 
            data=payload_to_verify,
            signature_b64=sig_to_verify
        )
        
        # Restore signature
        spike.signature = sig_to_verify
        
        if is_valid:
            print(f"[SECURITY] Ingress Verified: Node {peer_id[:8]}...")
            return True, "AUTHORIZED"
        else:
            return False, "DENIED: Invalid cryptographic signature (Tampered Data)."

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    gateway = SecurityGateway(db)
    
    # Setup Node Identity for test
    id_a = NodeIdentity()
    node_a_id = id_a.get_public_key_b64()
    
    # Register Node A in our DB so they are 'Trusted'
    db.update_peer(node_a_id, spikes=100, reward=1.0)
    
    # 1. Honest Spike (Correct Key)
    honest_spike = NeuralSpike(
        task_id="TEST_001", ingrvm_id="ingrvm_0", 
        node_id=node_a_id, input_hash="hash"
    )
    honest_spike.set_spikes([1])
    
    # Sign correctly: sign the binary of the spike with sig=None
    honest_spike.signature = None
    honest_spike.signature = id_a.sign_data(honest_spike.to_bin())
    
    ok, msg = gateway.verify_ingress(honest_spike)
    print(f"Test Honest: {msg}")
    
    # 2. Malicious Spike (Tampered after signing)
    tampered_spike = NeuralSpike(
        task_id="TEST_003", ingrvm_id="ingrvm_0", 
        node_id=node_a_id, input_hash="hash"
    )
    tampered_spike.set_spikes([1])
    tampered_spike.signature = id_a.sign_data(tampered_spike.to_bin())
    # TAMPER
    tampered_spike.task_id = "TAMPERED_TASK_ID"
    
    ok_bad, msg_bad = gateway.verify_ingress(tampered_spike)
    print(f"Test Tamper: {msg_bad}")
    
    if ok and not ok_bad:
        print("\nSUCCESS: Security Gateway successfully blocked unauthorized/tampered traffic.")
