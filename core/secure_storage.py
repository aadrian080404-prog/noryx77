"""Encrypted storage boundary for sensitive NORYX7 records.

The store keeps ciphertext, never plaintext, and authenticates the namespace and
record identity as associated data. A production backend can replace the
in-memory dictionary without changing the cryptographic contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from .crypto import AuthenticatedCipher, EncryptedEnvelope


@dataclass(frozen=True)
class StoredCiphertext:
    record_id: str
    envelope: EncryptedEnvelope


class EncryptedRecordStore:
    """Bounded encrypted record store; plaintext exists only at the API boundary."""

    def __init__(self, cipher: AuthenticatedCipher, *, namespace: str, max_records: int = 10_000):
        if not isinstance(cipher, AuthenticatedCipher):
            raise ValueError("cipher_required")
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace_required")
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1:
            raise ValueError("max_records must be a positive integer")
        self.cipher = cipher
        self.namespace = namespace
        self.max_records = max_records
        self._records: dict[str, StoredCiphertext] = {}

    def _aad(self, record_id: str) -> bytes:
        return f"noryx7/{self.namespace}/v1/{record_id}".encode("utf-8")

    def put(self, record_id: str, plaintext: bytes, *, key_id: str) -> None:
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id_required")
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext_must_be_bytes")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("key_id_required")
        if record_id not in self._records and len(self._records) >= self.max_records:
            raise MemoryError("storage_capacity_exceeded")
        envelope = self.cipher.encrypt(plaintext, key_id=key_id, aad=self._aad(record_id))
        self._records[record_id] = StoredCiphertext(record_id, envelope)

    def get(self, record_id: str) -> bytes | None:
        if not isinstance(record_id, str) or not record_id.strip():
            return None
        stored = self._records.get(record_id)
        if stored is None:
            return None
        if stored.envelope.aad != self._aad(record_id):
            raise ValueError("storage_metadata_integrity_failed")
        return self.cipher.decrypt(stored.envelope)

    def delete(self, record_id: str) -> bool:
        if not isinstance(record_id, str):
            return False
        return self._records.pop(record_id, None) is not None

    def __len__(self) -> int:
        return len(self._records)

    def snapshot_ciphertext(self) -> tuple[StoredCiphertext, ...]:
        """Return ciphertext records for a persistence backend; no plaintext is exposed."""
        return tuple(self._records.values())
