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
import re
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
    "issuer_key_id", "signature",
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
    if (isinstance(max_ttl_seconds, bool) or not isinstance(max_ttl_seconds, int)
            or not 1 <= max_ttl_seconds <= 604_800):
        raise MemoryTransferRejected("invalid_max_ttl")

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
    if not ciphertext or len(ciphertext) > _MAX_CIPHERTEXT:
        raise MemoryTransferRejected("invalid_ciphertext")
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
