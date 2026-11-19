"""Encrypted persistence adapter preserving exact memory ownership scopes."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .crypto import AuthenticatedCipher
from .memory import MemoryItem
from .secure_storage import EncryptedRecordStore, StoredCiphertext

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1


class EncryptedMemoryStore:
    """Persist scoped MemoryItems as ciphertext under scope-derived record IDs.

    Legacy v1 records remain readable only through their exact legacy scope.
    New writes use a digest of memory_id + principal + agent + execution, so
    different owners may safely reuse a logical memory_id.
    """

    MAX_EXECUTION_ID_BYTES = 256
    MAX_PRINCIPAL_ID_BYTES = 1024
    MAX_AGENT_ID_BYTES = 1024

    def __init__(self, cipher: AuthenticatedCipher, *, namespace: str = "memory", max_items: int = 10_000):
        self._store = EncryptedRecordStore(cipher, namespace=namespace, max_records=max_items)

    @staticmethod
    def _record_id(memory_id: str, principal_id: str, agent_id: str, execution_id: str) -> str:
        payload = json.dumps(
            [memory_id, principal_id, agent_id, execution_id],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(b"noryx7/encrypted-memory-scope/v2/" + payload).hexdigest()

    @classmethod
    def _validate_scope(cls, principal_id: str, agent_id: str, execution_id: str) -> bool:
        values = (
            (principal_id, cls.MAX_PRINCIPAL_ID_BYTES),
            (agent_id, cls.MAX_AGENT_ID_BYTES),
            (execution_id, cls.MAX_EXECUTION_ID_BYTES),
        )
        return all(
            isinstance(value, str) and len(value.encode("utf-8")) <= limit
            for value, limit in values
        )

    @classmethod
    def _serialize(cls, item: MemoryItem) -> bytes:
        if not isinstance(item, MemoryItem) or not isinstance(item.memory_id, str) or not item.memory_id:
            raise ValueError("memory_item_required")
        if not cls._validate_scope(item.principal_id, item.agent_id, item.execution_id):
            raise ValueError("invalid_memory_identity_scope")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "memory_id": item.memory_id,
            "content": item.content,
            "kind": item.kind,
            "source": item.source,
            "importance": float(item.importance),
            "execution_id": item.execution_id,
            "principal_id": item.principal_id,
            "agent_id": item.agent_id,
        }
        try:
            return json.dumps(
                payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("memory_content_not_persistable") from exc

    @classmethod
    def _deserialize(cls, record_id: str, plaintext: bytes) -> MemoryItem:
        try:
            payload: Any = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid_persisted_memory") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") not in (
            LEGACY_SCHEMA_VERSION, SCHEMA_VERSION
        ):
            raise ValueError("invalid_persisted_memory_schema")
        principal_id = payload.get("principal_id", "")
        agent_id = payload.get("agent_id", "")
        execution_id = payload.get("execution_id", "")
        if not cls._validate_scope(principal_id, agent_id, execution_id):
            raise ValueError("invalid_persisted_memory_scope")
        item = MemoryItem(
            memory_id=payload.get("memory_id", ""),
            content=payload.get("content"),
            kind=payload.get("kind", "working"),
            source=payload.get("source", ""),
            importance=payload.get("importance", 0.0),
            execution_id=execution_id,
            principal_id=principal_id,
            agent_id=agent_id,
        )
        if not isinstance(item.memory_id, str) or not item.memory_id:
            raise ValueError("invalid_persisted_memory")
        if not isinstance(item.kind, str) or not isinstance(item.source, str):
            raise ValueError("invalid_persisted_memory")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("invalid_persisted_memory")
        if payload["schema_version"] == LEGACY_SCHEMA_VERSION:
            if record_id != item.memory_id:
                raise ValueError("memory_identity_mismatch")
        elif record_id != cls._record_id(item.memory_id, principal_id, agent_id, execution_id):
            raise ValueError("memory_identity_mismatch")
        return item

    def put(self, item: MemoryItem, *, key_id: str) -> None:
        record_id = self._record_id(item.memory_id, item.principal_id, item.agent_id, item.execution_id)
        self._store.put(record_id, self._serialize(item), key_id=key_id)

    def get(
        self, memory_id: str, *, principal_id: str = "", agent_id: str = "",
        execution_id: str | None = None,
    ) -> MemoryItem | None:
        if execution_id is None:
            execution_id = ""
        if (
            not isinstance(memory_id, str) or not memory_id
            or not self._validate_scope(principal_id, agent_id, execution_id)
        ):
            return None
        record_id = self._record_id(memory_id, principal_id, agent_id, execution_id)
        plaintext = self._store.get(record_id)
        legacy = False
        if plaintext is None and not principal_id and not agent_id and not execution_id:
            plaintext = self._store.get(memory_id)
            legacy = plaintext is not None
        if plaintext is None:
            return None
        item = self._deserialize(memory_id if legacy else record_id, plaintext)
        if (
            item.memory_id != memory_id
            or item.principal_id != principal_id
            or item.agent_id != agent_id
            or item.execution_id != execution_id
        ):
            return None
        return item

    def delete(
        self, memory_id: str, *, principal_id: str = "", agent_id: str = "",
        execution_id: str | None = None,
    ) -> bool:
        if execution_id is None:
            execution_id = ""
        if (
            not isinstance(memory_id, str) or not memory_id
            or not self._validate_scope(principal_id, agent_id, execution_id)
        ):
            return False
        record_id = self._record_id(memory_id, principal_id, agent_id, execution_id)
        if self._store.delete(record_id):
            return True
        if principal_id or agent_id or execution_id:
            return False
        legacy = self._store.get(memory_id)
        if legacy is None:
            return False
        item = self._deserialize(memory_id, legacy)
        if item.principal_id or item.agent_id or item.execution_id:
            return False
        return self._store.delete(memory_id)

    def __len__(self) -> int:
        return len(self._store)

    def snapshot_ciphertext(self) -> tuple[StoredCiphertext, ...]:
        return self._store.snapshot_ciphertext()
