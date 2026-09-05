"""Fail-closed signed artifact admission primitives."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
@dataclass(frozen=True)
class SignedArtifact:
    artifact_id: str
    digest: str
    signer_id: str
    signature: bytes
    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, str) or not self.artifact_id.strip(): raise ValueError("invalid_artifact_id")
        if not isinstance(self.digest, str) or len(self.digest) != 64 or any(c not in "0123456789abcdef" for c in self.digest): raise ValueError("invalid_artifact_digest")
        if not isinstance(self.signer_id, str) or not self.signer_id.strip(): raise ValueError("invalid_signer_id")
        if not isinstance(self.signature, bytes) or len(self.signature) != 64: raise ValueError("invalid_signature")
class SupplyChainVerifier:
    def __init__(self) -> None:
        self._trusted: dict[str, Ed25519PublicKey] = {}
    def register(self, signer_id: str, public_key: Ed25519PublicKey) -> None:
        if signer_id in self._trusted: raise ValueError("signer_already_registered")
        if not isinstance(public_key, Ed25519PublicKey): raise TypeError("ed25519_key_required")
        self._trusted[signer_id] = public_key
    def revoke(self, signer_id: str) -> None:
        self._trusted.pop(signer_id, None)
    def verify(self, artifact: SignedArtifact, payload: bytes) -> bool:
        key = self._trusted.get(artifact.signer_id)
        if key is None or hashlib.sha256(payload).hexdigest() != artifact.digest: return False
        try:
            key.verify(artifact.signature, (artifact.artifact_id + ":" + artifact.digest).encode())
        except InvalidSignature:
            return False
        return True
