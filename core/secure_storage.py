"""Encrypted storage boundary for sensitive NORYX7 records.

The store keeps ciphertext, never plaintext, and authenticates the namespace and
record identity as associated data. A production backend can replace the
in-memory dictionary without changing the cryptographic contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from .crypto import AuthenticatedCipher, EncryptedEnvelope


@dataclass(frozen=True)
class StoredCiphertext:
    record_id: str
    envelope: EncryptedEnvelope


class EncryptedRecordStore:
    """Bounded encrypted record store; plaintext exists only at the API boundary."""

    MAX_RECORD_ID_BYTES = 256
    MAX_KEY_ID_BYTES = 256

    def __init__(self, cipher: AuthenticatedCipher, *, namespace: str, max_records: int = 10_000):
        if not isinstance(cipher, AuthenticatedCipher):
            raise ValueError("cipher_required")
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace_required")
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1:
            raise ValueError("max_records must be a positive integer")
        if len(namespace.encode("utf-8")) > self.MAX_RECORD_ID_BYTES:
            raise ValueError("namespace_too_large")
        self.cipher = cipher
        self.namespace = namespace
        self.max_records = max_records
        self._records: dict[str, StoredCiphertext] = {}
        self._lock = RLock()

    @classmethod
    def _valid_id(cls, value: str, limit: int) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= limit

    def _aad(self, record_id: str) -> bytes:
        return f"noryx7/{self.namespace}/v1/{record_id}".encode("utf-8")

    def put(self, record_id: str, plaintext: bytes, *, key_id: str) -> None:
        if not self._valid_id(record_id, self.MAX_RECORD_ID_BYTES):
            raise ValueError("record_id_required")
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext_must_be_bytes")
        if not self._valid_id(key_id, self.MAX_KEY_ID_BYTES):
            raise ValueError("key_id_required")
        envelope = self.cipher.encrypt(plaintext, key_id=key_id, aad=self._aad(record_id))
        with self._lock:
            if record_id not in self._records and len(self._records) >= self.max_records:
                raise MemoryError("storage_capacity_exceeded")
            self._records[record_id] = StoredCiphertext(record_id, envelope)

    def get(self, record_id: str) -> bytes | None:
        if not self._valid_id(record_id, self.MAX_RECORD_ID_BYTES):
            return None
        with self._lock:
            stored = self._records.get(record_id)
            if stored is None:
                return None
            if stored.envelope.aad != self._aad(record_id):
                raise ValueError("storage_metadata_integrity_failed")
            return self.cipher.decrypt(stored.envelope)

    def delete(self, record_id: str) -> bool:
        if not self._valid_id(record_id, self.MAX_RECORD_ID_BYTES):
            return False
        with self._lock:
            return self._records.pop(record_id, None) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def snapshot_ciphertext(self) -> tuple[StoredCiphertext, ...]:
        """Return ciphertext records for a persistence backend; no plaintext is exposed."""
        with self._lock:
            return tuple(self._records.values())
