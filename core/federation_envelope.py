"""Signed, replay-resistant execution envelopes for NORYX7 runtime federation.

This module defines a transport-neutral trust contract. It does not open
network connections or execute work. Callers must verify an envelope before
routing it to a runtime, then bind the returned identity/capabilities to the
runtime's own authorization and durable revocation registry.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
import sqlite3
import threading
import time
from typing import Callable, Mapping, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_DOMAIN = b"NORYX7/SIGNED_EXECUTION_ENVELOPE/v1\x00"
_MAX_TEXT_BYTES = 256
_MAX_CAPABILITIES = 128
_MAX_LIFETIME_SECONDS = 300
_MIN_NONCE_BYTES = 16
_MAX_NONCE_BYTES = 128


class EnvelopeRejected(PermissionError):
    """An execution envelope failed authentication, freshness or replay checks."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    if len(value.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{field}_too_long")
    return value


@dataclass(frozen=True)
class SignedExecutionEnvelope:
    schema_version: int
    execution_id: str
    principal_id: str
    agent_id: str
    task_type: str
    capabilities: tuple[str, ...]
    policy_version: str
    state_version: str
    issued_at: int
    expires_at: int
    nonce: bytes
    issuer_key_id: str
    signature: bytes = b""

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int) or self.schema_version != 1:
            raise ValueError("unsupported_envelope_schema")
        for value, field in (
            (self.execution_id, "execution_id"),
            (self.principal_id, "principal_id"),
            (self.agent_id, "agent_id"),
            (self.task_type, "task_type"),
            (self.policy_version, "policy_version"),
            (self.state_version, "state_version"),
            (self.issuer_key_id, "issuer_key_id"),
        ):
            _text(value, field)
        if not isinstance(self.capabilities, tuple) or not 1 <= len(self.capabilities) <= _MAX_CAPABILITIES:
            raise ValueError("invalid_capabilities")
        normalized = tuple(_text(value, "capability") for value in self.capabilities)
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate_capability")
        if isinstance(self.issued_at, bool) or not isinstance(self.issued_at, int) or self.issued_at < 0:
            raise ValueError("invalid_issued_at")
        if isinstance(self.expires_at, bool) or not isinstance(self.expires_at, int) or self.expires_at <= self.issued_at:
            raise ValueError("invalid_expires_at")
        if not isinstance(self.nonce, bytes) or not _MIN_NONCE_BYTES <= len(self.nonce) <= _MAX_NONCE_BYTES:
            raise ValueError("invalid_nonce")
        if not isinstance(self.signature, bytes) or (self.signature and len(self.signature) != 64):
            raise ValueError("invalid_signature")

    def canonical_bytes(self) -> bytes:
        payload = {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "principal_id": self.principal_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "capabilities": sorted(self.capabilities),
            "policy_version": self.policy_version,
            "state_version": self.state_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce.hex(),
            "issuer_key_id": self.issuer_key_id,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")


def sign_execution_envelope(
    envelope: SignedExecutionEnvelope,
    *,
    issuer_key_id: str,
    signing_key: Ed25519PrivateKey,
) -> SignedExecutionEnvelope:
    if not isinstance(envelope, SignedExecutionEnvelope):
        raise TypeError("signed_execution_envelope_required")
    if not isinstance(signing_key, Ed25519PrivateKey):
        raise TypeError("ed25519_private_signing_key_required")
    unsigned = replace(envelope, issuer_key_id=_text(issuer_key_id, "issuer_key_id"), signature=b"")
    return replace(unsigned, signature=signing_key.sign(_DOMAIN + unsigned.canonical_bytes()))


class ReplayStore(Protocol):
    def consume(self, issuer_key_id: str, nonce: bytes, expires_at: int, *, now: int) -> bool: ...


class SQLiteEnvelopeReplayStore:
    """Atomic, crash-persistent nonce consumption shared by verifier instances."""

    def __init__(self, database_path: str, *, busy_timeout_ms: int = 5000) -> None:
        if not isinstance(database_path, str) or not database_path.strip() or database_path == ":memory:":
            raise ValueError("persistent_replay_database_required")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or not 1 <= busy_timeout_ms <= 60000:
            raise ValueError("invalid_busy_timeout")
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            database_path, timeout=busy_timeout_ms / 1000,
            isolation_level=None, check_same_thread=False,
        )
        self._connection.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS consumed_envelope_nonces ("
            "nonce_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL CHECK(expires_at > 0))"
        )
        try:
            os.chmod(database_path, 0o600)
        except OSError as exc:
            self._connection.close()
            raise RuntimeError("replay_database_permissions_unavailable") from exc

    @staticmethod
    def _nonce_hash(issuer_key_id: str, nonce: bytes) -> str:
        return hashlib.sha256(
            issuer_key_id.encode("utf-8") + b"\x00" + nonce
        ).hexdigest()

    def consume(self, issuer_key_id: str, nonce: bytes, expires_at: int, *, now: int) -> bool:
        if not isinstance(issuer_key_id, str) or not issuer_key_id.strip():
            raise ValueError("invalid_issuer_key_id")
        if not isinstance(nonce, bytes) or not _MIN_NONCE_BYTES <= len(nonce) <= _MAX_NONCE_BYTES:
            raise ValueError("invalid_nonce")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (expires_at, now)) or expires_at <= now:
            raise ValueError("invalid_replay_expiry")
        nonce_hash = self._nonce_hash(issuer_key_id, nonce)
        with self._lock:
            connection = self._connection
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM consumed_envelope_nonces WHERE expires_at <= ?", (now,)
                )
                connection.execute(
                    "INSERT INTO consumed_envelope_nonces(nonce_hash, expires_at) VALUES (?, ?)",
                    (nonce_hash, expires_at),
                )
                connection.execute("COMMIT")
                return True
            except sqlite3.IntegrityError:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                return False
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class ExecutionEnvelopeVerifier:
    """Verifies issuer authority, freshness, revocation and one-use nonce."""

    def __init__(
        self,
        trusted_public_keys: Mapping[str, bytes | Ed25519PublicKey],
        replay_store: ReplayStore,
        *,
        is_issuer_revoked: Callable[[str], bool],
        is_principal_revoked: Callable[[str], bool],
        is_agent_revoked: Callable[[str], bool],
        clock: Callable[[], int] = lambda: int(time.time()),
        max_lifetime_seconds: int = _MAX_LIFETIME_SECONDS,
        allowed_clock_skew_seconds: int = 5,
    ) -> None:
        if not isinstance(trusted_public_keys, Mapping) or not trusted_public_keys:
            raise ValueError("trusted_issuers_required")
        if not callable(getattr(replay_store, "consume", None)):
            raise TypeError("replay_store_contract_required")
        if not all(callable(callback) for callback in (is_issuer_revoked, is_principal_revoked, is_agent_revoked, clock)):
            raise TypeError("issuer_principal_agent_revocation_and_clock_callbacks_required")
        if isinstance(max_lifetime_seconds, bool) or not isinstance(max_lifetime_seconds, int) or not 1 <= max_lifetime_seconds <= _MAX_LIFETIME_SECONDS:
            raise ValueError("invalid_max_lifetime")
        if isinstance(allowed_clock_skew_seconds, bool) or not isinstance(allowed_clock_skew_seconds, int) or not 0 <= allowed_clock_skew_seconds <= 60:
            raise ValueError("invalid_clock_skew")
        keys: dict[str, Ed25519PublicKey] = {}
        for key_id, value in trusted_public_keys.items():
            _text(key_id, "issuer_key_id")
            if isinstance(value, bytes):
                if len(value) != 32:
                    raise ValueError("ed25519_public_key_required")
                value = Ed25519PublicKey.from_public_bytes(value)
            if not isinstance(value, Ed25519PublicKey):
                raise TypeError("ed25519_public_key_required")
            keys[key_id] = value
        self._keys = keys
        self._replay_store = replay_store
        self._is_issuer_revoked = is_issuer_revoked
        self._is_principal_revoked = is_principal_revoked
        self._is_agent_revoked = is_agent_revoked
        self._clock = clock
        self._max_lifetime = max_lifetime_seconds
        self._skew = allowed_clock_skew_seconds

    def verify_and_consume(self, envelope: SignedExecutionEnvelope) -> SignedExecutionEnvelope:
        if not isinstance(envelope, SignedExecutionEnvelope) or len(envelope.signature) != 64:
            raise EnvelopeRejected("invalid_execution_envelope")
        key = self._keys.get(envelope.issuer_key_id)
        if key is None:
            raise EnvelopeRejected("unknown_execution_issuer")
        try:
            key.verify(envelope.signature, _DOMAIN + envelope.canonical_bytes())
        except (InvalidSignature, ValueError, TypeError):
            raise EnvelopeRejected("execution_envelope_signature_invalid") from None

        revocation_checks = (
            (self._is_issuer_revoked, envelope.issuer_key_id, "issuer"),
            (self._is_principal_revoked, envelope.principal_id, "principal"),
            (self._is_agent_revoked, envelope.agent_id, "agent"),
        )
        for check, identity, label in revocation_checks:
            try:
                if check(identity):
                    raise EnvelopeRejected(f"execution_{label}_revoked")
            except EnvelopeRejected:
                raise
            except Exception:
                raise EnvelopeRejected(f"{label}_revocation_check_unavailable") from None

        try:
            now = self._clock()
        except Exception:
            raise EnvelopeRejected("trusted_clock_unavailable") from None
        if isinstance(now, bool) or not isinstance(now, int) or now < 0:
            raise EnvelopeRejected("trusted_clock_unavailable")
        if envelope.issued_at > now + self._skew:
            raise EnvelopeRejected("execution_envelope_not_yet_valid")
        if envelope.expires_at <= now:
            raise EnvelopeRejected("execution_envelope_expired")
        if envelope.expires_at - envelope.issued_at > self._max_lifetime:
            raise EnvelopeRejected("execution_envelope_lifetime_exceeded")
        try:
            consumed = self._replay_store.consume(
                envelope.issuer_key_id, envelope.nonce, envelope.expires_at, now=now
            )
        except Exception:
            raise EnvelopeRejected("execution_replay_store_unavailable") from None
        if not consumed:
            raise EnvelopeRejected("execution_envelope_replayed")
        return envelope
