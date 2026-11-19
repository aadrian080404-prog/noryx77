"""Fail-closed interfaces for external signing keys and monotonic trust epochs.

This module deliberately provides protocols, not a fake persistent KMS or a
SQLite-backed "external" witness. Deployments must inject independently
protected implementations.
"""
from __future__ import annotations

from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core.identity import AgentIdentity, PUBLIC_KEY_SIZE, SIGNATURE_SIZE


class SigningKeyProvider(Protocol):
    """A key handle backed by KMS/HSM or an isolated platform keystore."""

    def public_key(self, key_id: str) -> bytes: ...

    def sign(self, key_id: str, message: bytes) -> bytes: ...


class MonotonicWitness(Protocol):
    """Independent monotonic state; must not share rollback domain with SQLite."""

    def read_epoch(self, namespace: str) -> int: ...

    def advance_epoch(self, namespace: str, expected_epoch: int, next_epoch: int) -> bool: ...


def sign_for_identity(
    provider: SigningKeyProvider,
    *,
    key_id: str,
    identity: AgentIdentity,
    message: bytes,
) -> bytes:
    """Sign only when the provider's public key is the registered identity key."""
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("invalid_key_id")
    if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
        raise ValueError("invalid_agent_identity")
    if not isinstance(message, bytes) or not message:
        raise ValueError("invalid_signing_message")
    if not callable(getattr(provider, "public_key", None)) or not callable(
        getattr(provider, "sign", None)
    ):
        raise TypeError("signing_key_provider_required")
    try:
        public_key = provider.public_key(key_id)
    except Exception:
        raise PermissionError("signing_key_unavailable") from None
    if not isinstance(public_key, bytes) or len(public_key) != PUBLIC_KEY_SIZE:
        raise PermissionError("signing_key_public_material_invalid")
    if public_key != identity.public_key:
        raise PermissionError("signing_key_identity_mismatch")
    try:
        signature = provider.sign(key_id, message)
    except Exception:
        raise PermissionError("signing_operation_failed") from None
    if not isinstance(signature, bytes) or len(signature) != SIGNATURE_SIZE:
        raise PermissionError("signing_operation_invalid_result")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (InvalidSignature, ValueError, TypeError):
        raise PermissionError("signing_operation_unverifiable") from None
    return signature


def require_witness_epoch(
    witness: MonotonicWitness,
    *,
    namespace: str,
    local_epoch: int,
) -> int:
    """Require exact equality between local durable epoch and external witness.

    Any mismatch is treated as rollback, incomplete recovery, or an inconsistent
    deployment. No automatic repair or downgrade is attempted.
    """
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("invalid_witness_namespace")
    if isinstance(local_epoch, bool) or not isinstance(local_epoch, int) or local_epoch < 0:
        raise ValueError("invalid_local_epoch")
    if not callable(getattr(witness, "read_epoch", None)):
        raise TypeError("monotonic_witness_required")
    try:
        witnessed = witness.read_epoch(namespace)
    except Exception:
        raise PermissionError("monotonic_witness_unavailable") from None
    if isinstance(witnessed, bool) or not isinstance(witnessed, int) or witnessed < 0:
        raise PermissionError("monotonic_witness_invalid_epoch")
    if witnessed != local_epoch:
        raise PermissionError("monotonic_epoch_mismatch")
    return witnessed


def advance_witness_epoch(
    witness: MonotonicWitness,
    *,
    namespace: str,
    expected_epoch: int,
    next_epoch: int,
) -> int:
    """Advance external epoch by exactly one; caller must then persist local state.

    If local persistence fails after this succeeds, startup remains fail-closed
    until an explicit recovery reconciles the two independently protected states.
    """
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("invalid_witness_namespace")
    for value, name in ((expected_epoch, "expected_epoch"), (next_epoch, "next_epoch")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid_{name}")
    if expected_epoch >= (2**64 - 1) or next_epoch != expected_epoch + 1:
        raise ValueError("invalid_witness_epoch_transition")
    if not callable(getattr(witness, "advance_epoch", None)):
        raise TypeError("monotonic_witness_required")
    try:
        advanced = witness.advance_epoch(namespace, expected_epoch, next_epoch)
    except Exception:
        raise PermissionError("monotonic_witness_unavailable") from None
    if advanced is not True:
        raise PermissionError("monotonic_witness_conflict")
    return next_epoch
