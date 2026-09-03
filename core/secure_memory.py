"""Encrypted persistence adapter for NORYX7 memory records.

Working memory remains in trusted process memory for efficiency. This adapter is
for long-term/suspended persistence: plaintext is serialized only at the API
boundary and the backing store retains authenticated ciphertext only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .crypto import AuthenticatedCipher, EncryptedEnvelope
from .memory import MemoryItem
from .secure_storage import EncryptedRecordStore, StoredCiphertext


SCHEMA_VERSION = 1


class EncryptedMemoryStore:
    """Persist JSON-compatible MemoryItems through the encrypted record store."""

    def __init__(
        self,
        cipher: AuthenticatedCipher,
        *,
        namespace: str = "memory",
        max_items: int = 10_000,
    ):
        self._store = EncryptedRecordStore(
            cipher,
            namespace=namespace,
            max_records=max_items,
        )

    @staticmethod
    def _serialize(item: MemoryItem) -> bytes:
        if not isinstance(item, MemoryItem):
            raise ValueError("memory_item_required")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "memory_id": item.memory_id,
            "content": item.content,
            "kind": item.kind,
            "source": item.source,
            "importance": float(item.importance),
        }
        try:
            return json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("memory_content_not_persistable") from exc

    @staticmethod
    def _deserialize(record_id: str, plaintext: bytes) -> MemoryItem:
        try:
            payload: Any = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid_persisted_memory") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("invalid_persisted_memory_schema")
        if payload.get("memory_id") != record_id:
            raise ValueError("memory_identity_mismatch")
        item = MemoryItem(
            memory_id=payload.get("memory_id", ""),
            content=payload.get("content"),
            kind=payload.get("kind", "working"),
            source=payload.get("source", ""),
            importance=payload.get("importance", 0.0),
        )
        if not item.memory_id or not isinstance(item.kind, str) or not isinstance(item.source, str):
            raise ValueError("invalid_persisted_memory")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("invalid_persisted_memory")
        return item

    def put(self, item: MemoryItem, *, key_id: str) -> None:
        self._store.put(item.memory_id, self._serialize(item), key_id=key_id)

    def get(self, memory_id: str) -> MemoryItem | None:
        plaintext = self._store.get(memory_id)
        if plaintext is None:
            return None
        return self._deserialize(memory_id, plaintext)

    def delete(self, memory_id: str) -> bool:
        return self._store.delete(memory_id)

    def __len__(self) -> int:
        return len(self._store)

    def snapshot_ciphertext(self) -> tuple[StoredCiphertext, ...]:
        return self._store.snapshot_ciphertext()
