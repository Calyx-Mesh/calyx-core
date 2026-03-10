import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

class NodeIdentity:
    """
    Manages the cryptographic identity of a INGRVM Node.
    Uses Ed25519 for high-speed signing and verification.
    """
    def __init__(self, key_path: str = "identity.key"):
        self.key_path = key_path
        self.private_key = None
        self.public_key = None
        self.load_or_create()

    def load_or_create(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(f.read())
            print("[IDENTITY] Loaded existing Node Identity.")
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            with open(self.key_path, "wb") as f:
                f.write(self.private_key.private_bytes_raw())
            print("[IDENTITY] Created NEW Node Identity.")
        
        self.public_key = self.private_key.public_key()

    def get_public_key_b64(self) -> str:
        """The public key string used as the network ID."""
        return base64.b64encode(self.public_key.public_bytes_raw()).decode("utf-8")

    def sign_data(self, data: bytes) -> str:
        """Signs binary data and returns a base64 signature."""
        signature = self.private_key.sign(data)
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def verify_signature(public_key_b64: str, data: bytes, signature_b64: str) -> bool:
        """Verifies that data was signed by the owner of the public key."""
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            sig_bytes = base64.b64decode(signature_b64)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            pub_key.verify(sig_bytes, data)
            return True
        except (InvalidSignature, Exception):
            return False

# --- Verification Test ---
if __name__ == "__main__":
    identity = NodeIdentity()
    node_id = identity.get_public_key_b64()
    print(f"Node ID: {node_id}")
    
    # Mock some Spike Data
    test_payload = b"NEURAL_SPIKE_BINARY_DATA_001"
    
    # Sign
    signature = identity.sign_data(test_payload)
    print(f"Signature: {signature[:32]}...")
    
    # Verify (Success case)
    is_valid = identity.verify_signature(node_id, test_payload, signature)
    print(f"Verification (Self): {'[PASS]' if is_valid else '[FAIL]'}")
    
    # Verify (Tamper case)
    is_valid_tamper = identity.verify_signature(node_id, b"TAMPERED_DATA", signature)
    print(f"Verification (Tamper): {'[PASS]' if is_valid_tamper else '[FAIL] (Correct)'}")
    
    if is_valid and not is_valid_tamper:
        print("\nSUCCESS: Cryptographic Identity system is secure.")
