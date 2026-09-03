from copy import deepcopy
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac

from .crypto import KeyProvider


@dataclass(frozen=True)
class AuditCheckpoint:
    """Authenticated checkpoint binding an audit-chain digest to a secret key."""

    version: int
    key_id: str
    digest: str
    mac: bytes

    def is_well_formed(self) -> bool:
        return (
            self.version == 1
            and isinstance(self.key_id, str)
            and bool(self.key_id.strip())
            and isinstance(self.digest, str)
            and len(self.digest) == 64
            and all(char in "0123456789abcdef" for char in self.digest)
            and isinstance(self.mac, bytes)
            and len(self.mac) == 32
        )


class AuditLog:
    """Append-only runtime evidence with tamper-evident and authenticated chaining."""

    _GENESIS = "0" * 64
    _CHECKPOINT_DOMAIN = b"noryx7/audit-checkpoint/v1/"

    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._digests: list[str] = []

    @classmethod
    def _canonicalize(cls, entry: dict[str, Any], previous_digest: str) -> bytes:
        payload = {"previous_digest": previous_digest, "entry": entry}
        try:
            return json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("audit data must be JSON serializable") from exc

    @classmethod
    def _digest(cls, entry: dict[str, Any], previous_digest: str) -> str:
        return hashlib.sha256(cls._canonicalize(entry, previous_digest)).hexdigest()

    @classmethod
    def _checkpoint_payload(cls, digest: str) -> bytes:
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid_audit_digest")
        return cls._CHECKPOINT_DOMAIN + digest.encode("ascii")

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        entry = {"event": event, **data}
        stored = deepcopy(entry)
        previous_digest = self._digests[-1] if self._digests else self._GENESIS
        digest = self._digest(stored, previous_digest)
        self._events.append(stored)
        self._digests.append(digest)
        return deepcopy(stored)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)

    def verify_integrity(self) -> bool:
        if len(self._events) != len(self._digests):
            return False
        previous_digest = self._GENESIS
        for entry, expected_digest in zip(self._events, self._digests):
            if not isinstance(entry, dict) or not isinstance(expected_digest, str):
                return False
            try:
                actual_digest = self._digest(entry, previous_digest)
            except (TypeError, ValueError):
                return False
            if actual_digest != expected_digest:
                return False
            previous_digest = expected_digest
        return True

    def digest(self) -> str:
        return self._digests[-1] if self._digests else self._GENESIS

    def checkpoint(self, provider: KeyProvider, *, key_id: str) -> AuditCheckpoint:
        """Create an authenticated external checkpoint of the current chain root."""
        if not isinstance(provider, KeyProvider):
            raise ValueError("key_provider_required")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        if not self.verify_integrity():
            raise ValueError("audit_integrity_failed")
        key = provider.get_key(key_id)
        if not isinstance(key, bytes) or not key:
            raise ValueError("audit_checkpoint_key_required")
        payload = self._checkpoint_payload(self.digest())
        signer = hmac.HMAC(key, hashes.SHA256())
        signer.update(payload)
        return AuditCheckpoint(1, key_id, self.digest(), signer.finalize())

    def verify_checkpoint(self, checkpoint: AuditCheckpoint, provider: KeyProvider) -> bool:
        """Verify a checkpoint against the current chain and the external secret."""
        if not isinstance(provider, KeyProvider) or not isinstance(checkpoint, AuditCheckpoint):
            return False
        if not checkpoint.is_well_formed() or not self.verify_integrity() or checkpoint.digest != self.digest():
            return False
        try:
            key = provider.get_key(checkpoint.key_id)
            if not isinstance(key, bytes) or not key:
                return False
            verifier = hmac.HMAC(key, hashes.SHA256())
            verifier.update(self._checkpoint_payload(checkpoint.digest))
            verifier.verify(checkpoint.mac)
            return True
        except (KeyError, TypeError, ValueError, InvalidSignature):
            return False
