"""Versioned, fail-closed contract for encrypted cross-runtime memory transfer.

This module validates an opaque ciphertext envelope. Cryptographic signature
verification, durable replay reservation, and recipient-key decryption are
injected from each runtime's trusted security boundary; this module does not
pretend that callbacks or a JSON envelope are cryptographic primitives.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any


_SCHEMA_VERSION = 1
_MAX_ID = 256
_MAX_NONCE = 256
_MAX_CIPHERTEXT = 1_000_000
_HEX_256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED = frozenset({
    "schema_version", "transfer_id", "source_principal_id",
    "recipient_principal_id", "source_agent_id", "recipient_agent_id",
    "execution_id", "recipient_key_id", "ciphertext_b64",
    "ciphertext_sha256", "issued_at", "expires_at", "nonce",
    "issuer_key_id", "ephemeral_public_key_b64", "aead_nonce_b64", "signature",
})


class MemoryTransferRejected(ValueError):
    """Raised when a transfer envelope cannot be safely accepted."""


def _text(value: Any, field: str, *, optional: bool = False, maximum: int = _MAX_ID) -> str:
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise MemoryTransferRejected(f"invalid_{field}")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise MemoryTransferRejected(f"invalid_{field}") from exc
    if size > maximum:
        raise MemoryTransferRejected(f"invalid_{field}")
    return value


def canonical_unsigned_envelope(envelope: Mapping[str, Any]) -> bytes:
    """Return deterministic bytes for signature verification; signature excluded."""
    if not isinstance(envelope, Mapping):
        raise MemoryTransferRejected("invalid_envelope")
    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    try:
        encoded = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise MemoryTransferRejected("non_canonical_envelope") from exc
    if len(encoded) > _MAX_CIPHERTEXT + 8_192:
        raise MemoryTransferRejected("envelope_too_large")
    return encoded


def validate_memory_transfer(
    envelope: Mapping[str, Any],
    *,
    expected_recipient_principal_id: str,
    expected_recipient_key_id: str,
    verify_signature: Callable[[str, bytes, str], bool],
    reserve_nonce: Callable[[str, str, int], bool],
    now: int | None = None,
    max_ttl_seconds: int = 86_400,
) -> bytes:
    """Verify an envelope and reserve its nonce; return ciphertext, never plaintext.

    verify_signature receives (issuer_key_id, canonical_unsigned_bytes, signature).
    reserve_nonce must durably and atomically reserve (issuer_key_id, nonce, expires_at)
    across restarts/replicas. A process-local set is not sufficient.
    """
    if not isinstance(envelope, Mapping) or set(envelope) != _REQUIRED:
        raise MemoryTransferRejected("invalid_envelope_fields")
    if envelope["schema_version"] != _SCHEMA_VERSION or isinstance(envelope["schema_version"], bool):
        raise MemoryTransferRejected("unsupported_schema_version")

    for field in ("transfer_id", "source_principal_id", "recipient_principal_id",
                  "execution_id", "recipient_key_id", "issuer_key_id", "signature"):
        _text(envelope[field], field)
    for field in ("source_agent_id", "recipient_agent_id"):
        _text(envelope[field], field, optional=True)
    _text(envelope["nonce"], "nonce", maximum=_MAX_NONCE)

    if envelope["recipient_principal_id"] != expected_recipient_principal_id:
        raise MemoryTransferRejected("recipient_principal_mismatch")
    if envelope["recipient_key_id"] != expected_recipient_key_id:
        raise MemoryTransferRejected("recipient_key_mismatch")
    if bool(envelope["source_agent_id"]) != bool(envelope["recipient_agent_id"]):
        raise MemoryTransferRejected("agent_scope_mapping_required")

    if (isinstance(max_ttl_seconds, bool) or not isinstance(max_ttl_seconds, int)
            or not 1 <= max_ttl_seconds <= 604_800):
        raise MemoryTransferRejected("invalid_max_ttl")
    issued_at, expires_at = envelope["issued_at"], envelope["expires_at"]
    if (isinstance(issued_at, bool) or not isinstance(issued_at, int)
            or isinstance(expires_at, bool) or not isinstance(expires_at, int)):
        raise MemoryTransferRejected("invalid_transfer_time")
    current = int(time.time()) if now is None else now
    if isinstance(current, bool) or not isinstance(current, int):
        raise MemoryTransferRejected("invalid_clock")
    if (issued_at > current or expires_at <= current
            or expires_at <= issued_at
            or expires_at - issued_at > max_ttl_seconds):
        raise MemoryTransferRejected("transfer_expired_or_invalid_ttl")
    digest = envelope["ciphertext_sha256"]
    if not isinstance(digest, str) or not _HEX_256.fullmatch(digest):
        raise MemoryTransferRejected("invalid_ciphertext_digest")
    encoded = envelope["ciphertext_b64"]
    if not isinstance(encoded, str) or len(encoded) > ((_MAX_CIPHERTEXT + 2) // 3) * 4:
        raise MemoryTransferRejected("invalid_ciphertext")
    try:
        ciphertext = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MemoryTransferRejected("invalid_ciphertext") from exc
    if len(ciphertext) < 16 or len(ciphertext) > _MAX_CIPHERTEXT:
        raise MemoryTransferRejected("invalid_ciphertext")
    try:
        ephemeral_public = base64.b64decode(envelope["ephemeral_public_key_b64"], validate=True)
        aead_nonce = base64.b64decode(envelope["aead_nonce_b64"], validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise MemoryTransferRejected("invalid_encryption_metadata") from exc
    if len(ephemeral_public) != 32 or len(aead_nonce) != 12:
        raise MemoryTransferRejected("invalid_encryption_metadata")
    if not hashlib.sha256(ciphertext).hexdigest() == digest:
        raise MemoryTransferRejected("ciphertext_digest_mismatch")

    signed = canonical_unsigned_envelope(envelope)
    try:
        verified = verify_signature(envelope["issuer_key_id"], signed, envelope["signature"]) is True
    except Exception:
        verified = False
    if not verified:
        raise MemoryTransferRejected("signature_verification_failed")

    try:
        reserved = reserve_nonce(envelope["issuer_key_id"], envelope["nonce"], expires_at) is True
    except Exception:
        reserved = False
    if not reserved:
        raise MemoryTransferRejected("replay_or_nonce_store_unavailable")
    return ciphertext


def ed25519_signature_verifier(
    key_resolver: Callable[[str], bytes | None],
) -> Callable[[str, bytes, str], bool]:
    """Build a fail-closed Ed25519 verifier from a trusted issuer-key resolver.

    The resolver must read keys from the runtime's authenticated trust store.
    The envelope never supplies its own verification key.
    """
    if not callable(key_resolver):
        raise TypeError("key_resolver_must_be_callable")

    def verify(issuer_key_id: str, payload: bytes, signature_b64: str) -> bool:
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            public_key = key_resolver(issuer_key_id)
            if not isinstance(public_key, bytes) or len(public_key) != 32:
                return False
            signature = base64.b64decode(signature_b64, validate=True)
            if len(signature) != 64:
                return False
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
            return True
        except Exception:
            return False

    return verify


class SQLiteNonceRegistry:
    """Durable, atomic single-database replay registry for one shared SQLite store.

    For multiple hosts, all verifiers must use the same strongly consistent
    database or a dedicated atomic nonce service; independent local files
    do not provide cluster-wide replay protection.
    """

    def __init__(self, db_path: str) -> None:
        if not isinstance(db_path, str) or not db_path.strip():
            raise ValueError("invalid_nonce_database_path")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            db_path, timeout=5.0, isolation_level=None, check_same_thread=False
        )
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS consumed_memory_transfer_nonces ("
                "issuer_key_id TEXT NOT NULL, nonce TEXT NOT NULL, "
                "expires_at INTEGER NOT NULL, PRIMARY KEY (issuer_key_id, nonce))"
            )

    def reserve(self, issuer_key_id: str, nonce: str, expires_at: int) -> bool:
        if (not isinstance(issuer_key_id, str) or not issuer_key_id
                or not isinstance(nonce, str) or not nonce
                or isinstance(expires_at, bool) or not isinstance(expires_at, int)):
            return False
        now = int(time.time())
        try:
            with self._lock:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    "DELETE FROM consumed_memory_transfer_nonces WHERE expires_at <= ?",
                    (now,),
                )
                self._conn.execute(
                    "INSERT INTO consumed_memory_transfer_nonces "
                    "(issuer_key_id, nonce, expires_at) VALUES (?, ?, ?)",
                    (issuer_key_id, nonce, expires_at),
                )
                self._conn.execute("COMMIT")
            return True
        except sqlite3.IntegrityError:
            with self._lock:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
            return False
        except sqlite3.Error:
            with self._lock:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
            return False

    def close(self) -> None:
        with self._lock:
            self._conn.close()



_AAD_FIELDS = (
    "schema_version", "transfer_id", "source_principal_id",
    "recipient_principal_id", "source_agent_id", "recipient_agent_id",
    "execution_id", "recipient_key_id", "issued_at", "expires_at",
    "nonce", "issuer_key_id", "ephemeral_public_key_b64", "aead_nonce_b64",
)


def memory_transfer_aad(envelope: Mapping[str, Any]) -> bytes:
    """Canonical authenticated metadata bound to the encrypted plaintext."""
    try:
        metadata = {field: envelope[field] for field in _AAD_FIELDS}
        return json.dumps(
            metadata, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
        raise MemoryTransferRejected("invalid_encryption_metadata") from exc


def seal_memory_transfer(
    plaintext: bytes,
    metadata: Mapping[str, Any],
    recipient_public_key: bytes,
) -> dict[str, Any]:
    """Encrypt memory to a recipient X25519 key with ChaCha20-Poly1305.

    The returned envelope has a placeholder signature; the trusted issuer must
    sign canonical_unsigned_envelope(envelope) after sealing.
    """
    if not isinstance(plaintext, bytes) or not plaintext or len(plaintext) > _MAX_CIPHERTEXT - 16:
        raise MemoryTransferRejected("invalid_plaintext")
    if not isinstance(recipient_public_key, bytes) or len(recipient_public_key) != 32:
        raise MemoryTransferRejected("invalid_recipient_public_key")
    base_fields = {
        "schema_version", "transfer_id", "source_principal_id",
        "recipient_principal_id", "source_agent_id", "recipient_agent_id",
        "execution_id", "recipient_key_id", "issued_at", "expires_at",
        "nonce", "issuer_key_id",
    }
    if not isinstance(metadata, Mapping) or set(metadata) != base_fields:
        raise MemoryTransferRejected("invalid_transfer_metadata")
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric.x25519 import (
            X25519PrivateKey, X25519PublicKey,
        )
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        ephemeral_private = X25519PrivateKey.generate()
        ephemeral_public = ephemeral_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        nonce = os.urandom(12)
        envelope = dict(metadata)
        envelope.update({
            "ephemeral_public_key_b64": base64.b64encode(ephemeral_public).decode("ascii"),
            "aead_nonce_b64": base64.b64encode(nonce).decode("ascii"),
        })
        aad = memory_transfer_aad(envelope)
        shared_secret = ephemeral_private.exchange(
            X25519PublicKey.from_public_bytes(recipient_public_key)
        )
        key = HKDF(
            algorithm=hashes.SHA256(), length=32,
            salt=hashlib.sha256(aad).digest(),
            info=b"NORYX7/federated-memory-transfer/v1",
        ).derive(shared_secret)
        ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, aad)
    except MemoryTransferRejected:
        raise
    except Exception as exc:
        raise MemoryTransferRejected("memory_encryption_failed") from exc

    envelope.update({
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "signature": "pending",
    })
    return envelope


def open_memory_transfer(
    envelope: Mapping[str, Any],
    *,
    recipient_private_key: bytes,
    expected_recipient_principal_id: str,
    expected_recipient_key_id: str,
    verify_signature: Callable[[str, bytes, str], bool],
    reserve_nonce: Callable[[str, str, int], bool],
    now: int | None = None,
    max_ttl_seconds: int = 86_400,
) -> bytes:
    """Authenticate, atomically consume the nonce, then decrypt for the recipient."""
    ciphertext = validate_memory_transfer(
        envelope,
        expected_recipient_principal_id=expected_recipient_principal_id,
        expected_recipient_key_id=expected_recipient_key_id,
        verify_signature=verify_signature,
        reserve_nonce=reserve_nonce,
        now=now,
        max_ttl_seconds=max_ttl_seconds,
    )
    if not isinstance(recipient_private_key, bytes) or len(recipient_private_key) != 32:
        raise MemoryTransferRejected("invalid_recipient_private_key")
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.x25519 import (
            X25519PrivateKey, X25519PublicKey,
        )
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        ephemeral_public = base64.b64decode(envelope["ephemeral_public_key_b64"], validate=True)
        nonce = base64.b64decode(envelope["aead_nonce_b64"], validate=True)
        private_key = X25519PrivateKey.from_private_bytes(recipient_private_key)
        shared_secret = private_key.exchange(X25519PublicKey.from_public_bytes(ephemeral_public))
        aad = memory_transfer_aad(envelope)
        key = HKDF(
            algorithm=hashes.SHA256(), length=32,
            salt=hashlib.sha256(aad).digest(),
            info=b"NORYX7/federated-memory-transfer/v1",
        ).derive(shared_secret)
        return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise MemoryTransferRejected("memory_decryption_failed") from exc
