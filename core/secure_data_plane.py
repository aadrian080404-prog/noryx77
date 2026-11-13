"""Tenant-bound envelope encryption for NORYX7 data-plane payloads.

This module deliberately contains no built-in production key store. A host must
supply a KMS/HSM-backed KeyProvider; plaintext data keys exist only transiently
inside the caller's process. Ciphertext and wrapped keys may be persisted or
transported without persisting plaintext.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 1
NONCE_SIZE = 12
DATA_KEY_SIZE = 32
MAX_CONTEXT_FIELD_BYTES = 512
MAX_WRAPPED_KEY_BYTES = 16 * 1024
DEFAULT_MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
VALID_CLASSIFICATIONS = frozenset({"public", "internal", "confidential", "restricted"})


class KeyProvider(Protocol):
    """KMS/HSM adapter. Production implementations must authenticate and audit calls."""

    def generate_data_key(self, *, tenant_id: str, purpose: str) -> tuple[bytes, bytes, str]:
        """Return (plaintext 256-bit data key, wrapped data key, immutable key version ID."""
        ...

    def unwrap_data_key(
        self, *, wrapped_key: bytes, key_id: str, tenant_id: str, purpose: str
    ) -> bytes:
        """Unwrap a data key only for the exact tenant and purpose context."""
        ...


@dataclass(frozen=True)
class EncryptedRecord:
    version: int
    tenant_id: str
    record_id: str
    purpose: str
    classification: str
    key_id: str
    wrapped_key: bytes
    nonce: bytes
    ciphertext: bytes
    aad_digest: str

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.version, int)
            and not isinstance(self.version, bool)
            and self.version == VERSION
            and _valid_context(self.tenant_id)
            and _valid_context(self.record_id)
            and _valid_context(self.purpose)
            and isinstance(self.classification, str)
            and self.classification in VALID_CLASSIFICATIONS
            and _valid_context(self.key_id)
            and isinstance(self.wrapped_key, bytes)
            and 1 <= len(self.wrapped_key) <= MAX_WRAPPED_KEY_BYTES
            and isinstance(self.nonce, bytes)
            and len(self.nonce) == NONCE_SIZE
            and isinstance(self.ciphertext, bytes)
            and 16 <= len(self.ciphertext) <= DEFAULT_MAX_PAYLOAD_BYTES + 16
            and isinstance(self.aad_digest, str)
            and len(self.aad_digest) == 64
            and all(ch in "0123456789abcdef" for ch in self.aad_digest)
        )


def _valid_context(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value.encode("utf-8")) <= MAX_CONTEXT_FIELD_BYTES
    )


def _associated_data(
    *,
    version: int,
    tenant_id: str,
    record_id: str,
    purpose: str,
    classification: str,
    key_id: str,
) -> bytes:
    context = {
        "version": version,
        "tenant_id": tenant_id,
        "record_id": record_id,
        "purpose": purpose,
        "classification": classification,
        "key_id": key_id,
    }
    return json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class SecureDataPlane:
    """Per-record AES-256-GCM envelope encryption with externally managed keys."""

    def __init__(self, key_provider: KeyProvider, *, max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES):
        if not callable(getattr(key_provider, "generate_data_key", None)) or not callable(
            getattr(key_provider, "unwrap_data_key", None)
        ):
            raise TypeError("kms_key_provider_required")
        if (
            isinstance(max_payload_bytes, bool)
            or not isinstance(max_payload_bytes, int)
            or not 1 <= max_payload_bytes <= DEFAULT_MAX_PAYLOAD_BYTES
        ):
            raise ValueError("invalid_max_payload_bytes")
        self._key_provider = key_provider
        self._max_payload_bytes = max_payload_bytes

    def encrypt(
        self,
        plaintext: bytes,
        *,
        tenant_id: str,
        record_id: str,
        purpose: str,
        classification: str = "restricted",
    ) -> EncryptedRecord:
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext_bytes_required")
        if len(plaintext) > self._max_payload_bytes:
            raise ValueError("payload_size_exceeded")
        if not all(_valid_context(item) for item in (tenant_id, record_id, purpose)):
            raise ValueError("invalid_encryption_context")
        if classification not in VALID_CLASSIFICATIONS:
            raise ValueError("invalid_data_classification")

        try:
            data_key, wrapped_key, key_id = self._key_provider.generate_data_key(
                tenant_id=tenant_id,
                purpose=purpose,
            )
        except Exception as exc:
            raise PermissionError("key_generation_unavailable") from exc

        if (
            not isinstance(data_key, bytes)
            or len(data_key) != DATA_KEY_SIZE
            or not isinstance(wrapped_key, bytes)
            or not 1 <= len(wrapped_key) <= MAX_WRAPPED_KEY_BYTES
            or not _valid_context(key_id)
        ):
            raise PermissionError("invalid_kms_key_material")

        nonce = secrets.token_bytes(NONCE_SIZE)
        aad = _associated_data(
            version=VERSION,
            tenant_id=tenant_id,
            record_id=record_id,
            purpose=purpose,
            classification=classification,
            key_id=key_id,
        )
        try:
            ciphertext = AESGCM(data_key).encrypt(nonce, plaintext, aad)
        except Exception as exc:
            raise RuntimeError("authenticated_encryption_failed") from exc

        return EncryptedRecord(
            VERSION,
            tenant_id,
            record_id,
            purpose,
            classification,
            key_id,
            bytes(wrapped_key),
            nonce,
            ciphertext,
            hashlib.sha256(aad).hexdigest(),
        )

    def decrypt(
        self,
        record: EncryptedRecord,
        *,
        tenant_id: str,
        record_id: str,
        purpose: str,
    ) -> bytes:
        if not isinstance(record, EncryptedRecord) or not record.is_well_formed():
            raise ValueError("invalid_encrypted_record")
        if (record.tenant_id, record.record_id, record.purpose) != (
            tenant_id,
            record_id,
            purpose,
        ):
            raise PermissionError("encrypted_record_context_mismatch")

        aad = _associated_data(
            version=record.version,
            tenant_id=record.tenant_id,
            record_id=record.record_id,
            purpose=record.purpose,
            classification=record.classification,
            key_id=record.key_id,
        )
        if not secrets.compare_digest(hashlib.sha256(aad).hexdigest(), record.aad_digest):
            raise PermissionError("encrypted_record_metadata_tampered")

        try:
            data_key = self._key_provider.unwrap_data_key(
                wrapped_key=record.wrapped_key,
                key_id=record.key_id,
                tenant_id=tenant_id,
                purpose=purpose,
            )
        except Exception as exc:
            raise PermissionError("key_unwrap_unavailable") from exc
        if not isinstance(data_key, bytes) or len(data_key) != DATA_KEY_SIZE:
            raise PermissionError("invalid_unwrapped_data_key")

        try:
            return AESGCM(data_key).decrypt(record.nonce, record.ciphertext, aad)
        except InvalidTag as exc:
            raise PermissionError("ciphertext_authentication_failed") from exc
        except Exception as exc:
            raise PermissionError("authenticated_decryption_failed") from exc
