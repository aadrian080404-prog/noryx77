"""Threshold authorization primitives for high-risk NORYX7 operations."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

MAX_PARTIES = 32
MAX_ID = 256
SIGNATURE_SIZE = 64
_DOMAIN = b"noryx7/multiauth/v1/"


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_ID:
        raise ValueError(f"invalid_{name}")
    return value


def action_digest(action_id: str, epoch: int, action_statement: bytes = b"") -> bytes:
    """Return a domain-separated digest binding approvals to one action/epoch."""
    _id(action_id, "action_id")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError("invalid_epoch")
    if not isinstance(action_statement, bytes):
        raise TypeError("action_statement_must_be_bytes")
    h = hashlib.sha256()
    h.update(_DOMAIN)
    raw_id = action_id.encode("utf-8")
    h.update(len(raw_id).to_bytes(4, "big")); h.update(raw_id)
    h.update(epoch.to_bytes(8, "big"))
    h.update(len(action_statement).to_bytes(8, "big")); h.update(action_statement)
    return h.digest()


@dataclass(frozen=True)
class AuthorizationProof:
    """Legacy structural proof retained for compatibility; not cryptographic."""
    action_id: str
    approvers: tuple[str, ...]
    threshold: int
    epoch: int

    def __post_init__(self) -> None:
        _id(self.action_id, "action_id")
        if not self.approvers or len(self.approvers) > MAX_PARTIES:
            raise ValueError("invalid_approvers")
        if len(set(self.approvers)) != len(self.approvers):
            raise ValueError("duplicate_approver")
        for party in self.approvers:
            _id(party, "approver")
        if not isinstance(self.threshold, int) or not 1 <= self.threshold <= len(self.approvers):
            raise ValueError("invalid_threshold")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise ValueError("invalid_epoch")


@dataclass(frozen=True)
class SignedApproval:
    approver_id: str
    public_key: bytes
    signature: bytes

    def __post_init__(self) -> None:
        _id(self.approver_id, "approver_id")
        if not isinstance(self.public_key, bytes) or len(self.public_key) != 32:
            raise ValueError("invalid_public_key")
        if not isinstance(self.signature, bytes) or len(self.signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_signature")


@dataclass(frozen=True)
class SignedAuthorizationProof:
    action_id: str
    epoch: int
    action_statement: bytes
    approvals: tuple[SignedApproval, ...]
    threshold: int

    def __post_init__(self) -> None:
        _id(self.action_id, "action_id")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("invalid_epoch")
        if not isinstance(self.action_statement, bytes):
            raise TypeError("action_statement_must_be_bytes")
        if not self.approvals or len(self.approvals) > MAX_PARTIES:
            raise ValueError("invalid_approvals")
        if any(not isinstance(a, SignedApproval) for a in self.approvals):
            raise TypeError("invalid_approval")
        if len({a.approver_id for a in self.approvals}) != len(self.approvals):
            raise ValueError("duplicate_approver")
        if not isinstance(self.threshold, int) or isinstance(self.threshold, bool) or not 1 <= self.threshold <= len(self.approvals):
            raise ValueError("invalid_threshold")


class SignedApprovalAuthority:
    """Verifies independent Ed25519 approvals against a canonical action digest."""

    def __init__(self, *, required_threshold: int, trusted_keys: dict[str, bytes] | None = None) -> None:
        if not isinstance(required_threshold, int) or isinstance(required_threshold, bool) or not 1 <= required_threshold <= MAX_PARTIES:
            raise ValueError("invalid_required_threshold")
        self._required = required_threshold
        self._keys: dict[str, bytes] = {}
        self._lock = threading.RLock()
        for approver_id, public_key in (trusted_keys or {}).items():
            self.register(approver_id, public_key)

    @property
    def required_threshold(self) -> int:
        return self._required

    def register(self, approver_id: str, public_key: bytes) -> None:
        _id(approver_id, "approver_id")
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            raise ValueError("invalid_public_key")
        with self._lock:
            if approver_id in self._keys:
                raise ValueError("approver_already_registered")
            self._keys[approver_id] = bytes(public_key)

    def revoke(self, approver_id: str) -> None:
        _id(approver_id, "approver_id")
        with self._lock:
            self._keys.pop(approver_id, None)

    def verify(self, proof: SignedAuthorizationProof, *, action_id: str, epoch: int, action_statement: bytes = b"") -> bool:
        if not isinstance(proof, SignedAuthorizationProof):
            return False
        if proof.action_id != action_id or proof.epoch != epoch or proof.threshold < self._required:
            return False
        if proof.action_statement != action_statement:
            return False
        digest = action_digest(action_id, epoch, action_statement)
        with self._lock:
            valid = sum(1 for approval in proof.approvals if self._valid(approval, digest))
            return valid >= self._required

    def _valid(self, approval: SignedApproval, digest: bytes) -> bool:
        trusted = self._keys.get(approval.approver_id)
        if trusted is None or trusted != approval.public_key:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(approval.public_key).verify(approval.signature, digest)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


class ThresholdAuthorizer:
    """Requires explicit independent principals for privileged operations."""

    def __init__(self, *, required_threshold: int) -> None:
        if not isinstance(required_threshold, int) or required_threshold < 1 or required_threshold > MAX_PARTIES:
            raise ValueError("invalid_required_threshold")
        self._required = required_threshold

    @property
    def required_threshold(self) -> int:
        return self._required

    def verify(self, proof: AuthorizationProof, *, action_id: str, epoch: int) -> bool:
        return (
            proof.action_id == action_id
            and proof.epoch == epoch
            and proof.threshold >= self._required
            and len(proof.approvers) >= self._required
        )


def sign_approval(approver_id: str, private_key: Ed25519PrivateKey, *, action_id: str, epoch: int, action_statement: bytes = b"") -> SignedApproval:
    _id(approver_id, "approver_id")
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key_must_be_ed25519")
    public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return SignedApproval(approver_id, public_key, private_key.sign(action_digest(action_id, epoch, action_statement)))
