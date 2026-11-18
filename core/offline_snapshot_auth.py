"""Ed25519 authentication for portable NORYX7 offline authorization snapshots.

The issuer private key must remain in a trusted signing service or HSM.
Verifiers receive only pinned public keys. The unkeyed snapshot digest is
retained for corruption detection; this signature establishes issuer authority.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .offline import OfflineSnapshot

_DOMAIN = b"NORYX7/OFFLINE_SNAPSHOT_AUTH/v1\\x00"


def sign_offline_snapshot(
    snapshot: OfflineSnapshot,
    *,
    issuer_key_id: str,
    signing_key: Ed25519PrivateKey,
) -> OfflineSnapshot:
    """Return a snapshot with a canonical digest and detached Ed25519 signature."""
    if not isinstance(snapshot, OfflineSnapshot):
        raise TypeError("offline_snapshot_required")
    if not isinstance(issuer_key_id, str) or not issuer_key_id.strip():
        raise ValueError("offline_snapshot_issuer_key_id_required")
    if not isinstance(signing_key, Ed25519PrivateKey):
        raise TypeError("ed25519_private_signing_key_required")
    unsigned = replace(
        snapshot,
        integrity_digest="0" * 64,
        issuer_key_id=issuer_key_id,
        signature=b"",
    )
    digest = hashlib.sha256(unsigned.canonical_bytes()).hexdigest()
    prepared = replace(unsigned, integrity_digest=digest)
    signature = signing_key.sign(_DOMAIN + prepared.canonical_bytes())
    return replace(prepared, signature=signature)


class Ed25519OfflineSnapshotAuthenticator:
    """Callable verifier using an explicit allowlist of issuer public keys."""

    def __init__(self, trusted_public_keys: Mapping[str, bytes | Ed25519PublicKey]):
        if not isinstance(trusted_public_keys, Mapping) or not trusted_public_keys:
            raise ValueError("offline_snapshot_trusted_issuers_required")
        keys: dict[str, Ed25519PublicKey] = {}
        for key_id, value in trusted_public_keys.items():
            if not isinstance(key_id, str) or not key_id.strip():
                raise ValueError("offline_snapshot_issuer_key_id_required")
            if isinstance(value, bytes):
                if len(value) != 32:
                    raise ValueError("offline_snapshot_ed25519_public_key_required")
                value = Ed25519PublicKey.from_public_bytes(value)
            if not isinstance(value, Ed25519PublicKey):
                raise TypeError("offline_snapshot_ed25519_public_key_required")
            keys[key_id] = value
        self._trusted_public_keys = keys

    def __call__(self, snapshot: OfflineSnapshot) -> bool:
        if not isinstance(snapshot, OfflineSnapshot):
            return False
        if not snapshot.verify_integrity() or len(snapshot.signature) != 64:
            return False
        public_key = self._trusted_public_keys.get(snapshot.issuer_key_id)
        if public_key is None:
            return False
        try:
            public_key.verify(
                snapshot.signature,
                _DOMAIN + snapshot.canonical_bytes(),
            )
        except (InvalidSignature, ValueError, TypeError):
            return False
        return True