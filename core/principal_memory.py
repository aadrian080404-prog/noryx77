"""Process-local principal-scoped memory isolation.

This adapter partitions a bounded MemoryHierarchy by authenticated principal
identifier. It is not an identity provider, durable store, encryption layer,
or cross-device replication protocol.
"""
from __future__ import annotations

from threading import RLock

from .memory_hierarchy import MemoryHierarchy, MemoryRecord


class PrincipalMemoryHierarchy:
    MAX_PRINCIPAL_ID_BYTES = 256
    MAX_PRINCIPALS = 100_000

    def __init__(self, *, records_per_principal: int = 10_000, max_principals: int = 10_000):
        if isinstance(records_per_principal, bool) or not isinstance(records_per_principal, int):
            raise ValueError("invalid_principal_memory_capacity")
        if not 1 <= records_per_principal <= MemoryHierarchy.MAX_CAPACITY:
            raise ValueError("invalid_principal_memory_capacity")
        if isinstance(max_principals, bool) or not isinstance(max_principals, int):
            raise ValueError("invalid_principal_count")
        if not 1 <= max_principals <= self.MAX_PRINCIPALS:
            raise ValueError("invalid_principal_count")
        self._records_per_principal = records_per_principal
        self._max_principals = max_principals
        self._stores: dict[str, MemoryHierarchy] = {}
        self._lock = RLock()

    @classmethod
    def _valid_principal(cls, principal_id: object) -> bool:
        return (
            isinstance(principal_id, str)
            and bool(principal_id.strip())
            and len(principal_id.encode("utf-8")) <= cls.MAX_PRINCIPAL_ID_BYTES
        )

    def _store(self, principal_id: str, *, create: bool) -> MemoryHierarchy | None:
        if not self._valid_principal(principal_id):
            raise ValueError("invalid_memory_principal")
        store = self._stores.get(principal_id)
        if store is None and create:
            if len(self._stores) >= self._max_principals:
                raise MemoryError("principal_memory_capacity_reached")
            store = MemoryHierarchy(self._records_per_principal)
            self._stores[principal_id] = store
        return store

    def put(self, principal_id: str, record: MemoryRecord) -> None:
        with self._lock:
            store = self._store(principal_id, create=True)
            assert store is not None
            store.put(record)

    def get(self, principal_id: str, key: str) -> MemoryRecord | None:
        with self._lock:
            store = self._store(principal_id, create=False)
            return None if store is None else store.get(key)

    def promote(self, principal_id: str, key: str, level) -> MemoryRecord:
        with self._lock:
            store = self._store(principal_id, create=False)
            if store is None:
                raise KeyError(key)
            return store.promote(key, level)

    def delete(self, principal_id: str, key: str) -> bool:
        with self._lock:
            store = self._store(principal_id, create=False)
            return False if store is None else store.delete(key)

    def snapshot(self, principal_id: str) -> tuple[MemoryRecord, ...]:
        with self._lock:
            store = self._store(principal_id, create=False)
            return () if store is None else store.snapshot()

    def delete_principal(self, principal_id: str) -> bool:
        with self._lock:
            if not self._valid_principal(principal_id):
                raise ValueError("invalid_memory_principal")
            return self._stores.pop(principal_id, None) is not None

    def principal_count(self) -> int:
        with self._lock:
            return len(self._stores)
