import json
import time
import hashlib
import msgpack
import os
from typing import List, Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

# Task #10: Secure Mesh PSK
DEFAULT_PSK = os.getenv("INGRVM_SECURE_PSK", "INGRVM_SECURE_2026")
# Derive a 32-byte key from the PSK
SECURE_KEY = hashlib.sha256(DEFAULT_PSK.encode()).digest()

if HAS_PYDANTIC:
    class NeuralSpike(BaseModel):
        """
        The 'Blockchain-Ready' protocol for neuromorphic data transmission.
        Optimized with Sparse-Vector Encoding for massive bandwidth reduction.
        """
        task_id: str
        ingrvm_id: str
        node_id: str
        timestamp: float = Field(default_factory=time.time)
        
        # PIPELINE ROUTING
        current_layer: int = 0
        target_layer: Optional[int] = None
        model_name: str = "INGRVM-1.0"
        
        # MESH SAFETY (Task #04)
        ttl: int = 10 # Max hops before the spike is dropped
        hop_count: int = 0
        
        # OPTIMIZATION: Sparse Encoding
        sparse_indices: List[int] = []
        vector_size: int = 0
        
        input_hash: str
        witness_hash: Optional[str] = None
        signature: Optional[str] = None
        
        # Laptop Update: zk-PoI Proof
        poi_packet: Optional[Dict] = None
        
        # Task #10: Encryption Metadata
        is_encrypted: bool = False
        encrypted_payload: Optional[bytes] = None

        def set_spikes(self, dense_spikes: List[int]):
            """Converts a dense list to sparse indices."""
            self.vector_size = len(dense_spikes)
            self.sparse_indices = [i for i, val in enumerate(dense_spikes) if val > 0]

        def get_spikes(self) -> List[int]:
            """Reconstructs the dense list from sparse indices."""
            if self.is_encrypted and not self.sparse_indices and self.encrypted_payload:
                raise ValueError("Spike is encrypted. Decrypt before accessing indices.")
            
            dense = [0] * self.vector_size
            for idx in self.sparse_indices:
                if idx < self.vector_size:
                    dense[idx] = 1
            return dense

        def encrypt(self, key: bytes = SECURE_KEY):
            """ Task #10: Encrypts the spike payload using AES-GCM. """
            if self.is_encrypted: return
            
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            
            # We only encrypt the sparse data to preserve routing headers
            sensitive_data = {
                "sparse_indices": self.sparse_indices,
                "vector_size": self.vector_size,
                "input_hash": self.input_hash
            }
            data_bin = msgpack.packb(sensitive_data)
            ciphertext = aesgcm.encrypt(nonce, data_bin, self.task_id.encode())
            
            self.encrypted_payload = nonce + ciphertext
            self.sparse_indices = []
            self.is_encrypted = True

        def decrypt(self, key: bytes = SECURE_KEY):
            """ Task #10: Decrypts the spike payload. """
            if not self.is_encrypted or not self.encrypted_payload: return
            
            aesgcm = AESGCM(key)
            nonce = self.encrypted_payload[:12]
            ciphertext = self.encrypted_payload[12:]
            
            try:
                decrypted_data = aesgcm.decrypt(nonce, ciphertext, self.task_id.encode())
                sensitive_data = msgpack.unpackb(decrypted_data, raw=False)
                
                self.sparse_indices = sensitive_data["sparse_indices"]
                self.vector_size = sensitive_data["vector_size"]
                self.input_hash = sensitive_data["input_hash"]
                self.is_encrypted = False
                self.encrypted_payload = None
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")

        def to_bin(self) -> bytes:
            """Returns ultra-compact MessagePack binary."""
            return msgpack.packb(self.model_dump(), use_bin_type=True)

        @classmethod
        def from_bin(cls, data: bytes):
            unpacked = msgpack.unpackb(data, raw=False)
            return cls(**unpacked)
else:
    class NeuralSpike:
        """ Fallback for environments without Pydantic (e.g. some Termux builds). """
        def __init__(self, **kwargs):
            self.task_id = kwargs.get('task_id')
            self.ingrvm_id = kwargs.get('ingrvm_id')
            self.node_id = kwargs.get('node_id')
            self.timestamp = kwargs.get('timestamp', time.time())
            self.current_layer = kwargs.get('current_layer', 0)
            self.target_layer = kwargs.get('target_layer')
            self.model_name = kwargs.get('model_name', "INGRVM-1.0")
            self.ttl = kwargs.get('ttl', 10)
            self.hop_count = kwargs.get('hop_count', 0)
            self.sparse_indices = kwargs.get('sparse_indices', [])
            self.vector_size = kwargs.get('vector_size', 0)
            self.input_hash = kwargs.get('input_hash')
            self.witness_hash = kwargs.get('witness_hash')
            self.signature = kwargs.get('signature')
            self.poi_packet = kwargs.get('poi_packet')
            self.is_encrypted = kwargs.get('is_encrypted', False)
            self.encrypted_payload = kwargs.get('encrypted_payload')

        def set_spikes(self, dense_spikes: List[int]):
            self.vector_size = len(dense_spikes)
            self.sparse_indices = [i for i, val in enumerate(dense_spikes) if val > 0]

        def get_spikes(self) -> List[int]:
            if self.is_encrypted and not self.sparse_indices and self.encrypted_payload:
                raise ValueError("Spike is encrypted. Decrypt before accessing indices.")

            dense = [0] * self.vector_size
            for idx in self.sparse_indices:
                if idx < self.vector_size:
                    dense[idx] = 1
            return dense

        def encrypt(self, key: bytes = SECURE_KEY):
            """ Task #10: Encrypts the spike payload using AES-GCM. """
            if self.is_encrypted: return

            aesgcm = AESGCM(key)
            nonce = os.urandom(12)

            sensitive_data = {
                "sparse_indices": self.sparse_indices,
                "vector_size": self.vector_size,
                "input_hash": self.input_hash
            }
            data_bin = msgpack.packb(sensitive_data)
            ciphertext = aesgcm.encrypt(nonce, data_bin, self.task_id.encode())

            self.encrypted_payload = nonce + ciphertext
            self.sparse_indices = []
            self.is_encrypted = True

        def decrypt(self, key: bytes = SECURE_KEY):
            """ Task #10: Decrypts the spike payload. """
            if not self.is_encrypted or not self.encrypted_payload: return

            aesgcm = AESGCM(key)
            nonce = self.encrypted_payload[:12]
            ciphertext = self.encrypted_payload[12:]

            try:
                decrypted_data = aesgcm.decrypt(nonce, ciphertext, self.task_id.encode())
                sensitive_data = msgpack.unpackb(decrypted_data, raw=False)

                self.sparse_indices = sensitive_data["sparse_indices"]
                self.vector_size = sensitive_data["vector_size"]
                self.input_hash = sensitive_data["input_hash"]
                self.is_encrypted = False
                self.encrypted_payload = None
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")

        def to_dict(self):

            return {
                "task_id": self.task_id,
                "ingrvm_id": self.ingrvm_id,
                "node_id": self.node_id,
                "timestamp": self.timestamp,
                "current_layer": self.current_layer,
                "target_layer": self.target_layer,
                "model_name": self.model_name,
                "ttl": self.ttl,
                "hop_count": self.hop_count,
                "sparse_indices": self.sparse_indices,
                "vector_size": self.vector_size,
                "input_hash": self.input_hash,
                "witness_hash": self.witness_hash,
                "signature": self.signature,
                "poi_packet": self.poi_packet,
                "is_encrypted": self.is_encrypted,
                "encrypted_payload": self.encrypted_payload
            }

        def to_bin(self) -> bytes:
            return msgpack.packb(self.to_dict(), use_bin_type=True)

        @classmethod
        def from_bin(cls, data: bytes):
            unpacked = msgpack.unpackb(data, raw=False)
            return cls(**unpacked)

# --- LAN Socket Helper ---
import socket
import trio

async def send_spike_raw(spike: 'NeuralSpike', ip: str, port: int = 60005, timeout: int = 5) -> bool:
    """Sends a spike via raw TCP socket (Trio-friendly)."""
    try:
        with trio.move_on_after(timeout):
            async with await trio.open_tcp_stream(ip, port) as stream:
                await stream.send_all(spike.to_bin())
                return True
        return False # Timed out
    except Exception:
        return False

def generate_task_id(node_id: str, ingrvm_id: str) -> str:
    raw_id = f"{node_id}-{ingrvm_id}-{time.time()}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:16]

def hash_input(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

