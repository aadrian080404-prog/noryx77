"""Supply-chain integrity primitives for dependencies, models, firmware and updates."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_COMPONENT_ID = 256
MAX_VERSION = 256


@dataclass(frozen=True)
class ArtifactManifest:
    component_id: str
    version: str
    artifact_digest: str
    signer_key: bytes
    signature: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.component_id, str) or not self.component_id or len(self.component_id) > MAX_COMPONENT_ID:
            raise ValueError("invalid_component_id")
        if not isinstance(self.version, str) or not self.version or len(self.version) > MAX_VERSION:
            raise ValueError("invalid_version")
        if (
            not isinstance(self.artifact_digest, str)
            or len(self.artifact_digest) != 64
            or any(char not in "0123456789abcdef" for char in self.artifact_digest)
        ):
            raise ValueError("invalid_artifact_digest")
        if not isinstance(self.signer_key, bytes) or len(self.signer_key) != 32:
            raise ValueError("invalid_signer_key")
        if not isinstance(self.signature, bytes) or len(self.signature) != 64:
            raise ValueError("invalid_signature")


def manifest_digest(component_id: str, version: str, artifact_digest: str) -> bytes:
    payload = f"noryx7/supply-chain/v1|{component_id}|{version}|{artifact_digest}".encode()
    return hashlib.sha256(payload).digest()


class SupplyChainVerifier:
    """Allow only artifacts signed by explicitly trusted release keys."""

    def __init__(self, trusted_keys: set[bytes] | None = None) -> None:
        self._trusted = {bytes(key) for key in (trusted_keys or set())}
        if any(len(key) != 32 for key in self._trusted):
            raise ValueError("invalid_trusted_key")

    def verify(self, manifest: ArtifactManifest) -> bool:
        """Verify the signed manifest and its trusted signer identity."""
        if not isinstance(manifest, ArtifactManifest) or manifest.signer_key not in self._trusted:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(manifest.signer_key).verify(
                manifest.signature,
                manifest_digest(manifest.component_id, manifest.version, manifest.artifact_digest),
            )
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    def verify_artifact(self, manifest: ArtifactManifest, artifact: bytes) -> bool:
        """Verify both the signed manifest and the actual artifact bytes."""
        if not isinstance(manifest, ArtifactManifest) or not isinstance(artifact, bytes):
            return False
        if hashlib.sha256(artifact).hexdigest() != manifest.artifact_digest:
            return False
        return self.verify(manifest)
