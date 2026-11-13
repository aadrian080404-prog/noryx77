"""Explicit memory-tier routing across volatile and injected durable backends.

This is a local routing layer, not a distributed replication or consensus fabric.
"""
from __future__ import annotations

from threading import RLock

from .memory import MemoryItem, MemoryStore


class TieredMemoryRouter:
    """Routes memory kinds to explicit stores without silent tier fallback."""

    _KINDS = frozenset({"working", "local", "edge", "cloud", "long_term", "suspended"})

    def __init__(
        self,
        *,
        working_store: MemoryStore | None = None,
        local_store: MemoryStore | None = None,
        edge_store: MemoryStore | None = None,
        cloud_store: MemoryStore | None = None,
        require_durable_local: bool = True,
    ) -> None:
        if not isinstance(require_durable_local, bool):
            raise TypeError("require_durable_local_must_be_bool")
        if working_store is None:
            working_store = MemoryStore()
        if not isinstance(working_store, MemoryStore):
            raise TypeError("working_store_must_be_MemoryStore")
        for name, store in (
            ("local_store", local_store),
            ("edge_store", edge_store),
            ("cloud_store", cloud_store),
        ):
            if store is not None and not isinstance(store, MemoryStore):
                raise TypeError(name + "_must_be_MemoryStore")
        if require_durable_local and (
            local_store is None or not getattr(local_store, "durable", False)
        ):
            raise ValueError("durable_local_memory_store_required")
        self._stores = {
            "working": working_store,
            "local": local_store,
            "edge": edge_store,
            "cloud": cloud_store,
        }
        self._lock = RLock()
        self._closed = False

    @property
    def durable(self) -> bool:
        local = self._stores["local"]
        return (
            not self._closed
            and local is not None
            and bool(getattr(local, "durable", False))
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("memory_fabric_closed")

    def _backend_for_kind(self, kind: str) -> MemoryStore:
        if kind not in self._KINDS:
            raise ValueError("unsupported_memory_kind")
        tier = "working" if kind == "working" else kind
        if tier in {"long_term", "suspended"}:
            tier = "local"
        store = self._stores.get(tier)
        if store is None:
            raise RuntimeError("memory_tier_unavailable:" + tier)
        if tier == "local" and not getattr(store, "durable", False):
            raise RuntimeError("memory_tier_not_durable:local")
        return store

    def _unique_stores(self) -> tuple[MemoryStore, ...]:
        result = []
        seen = set()
        for store in self._stores.values():
            if store is not None and id(store) not in seen:
                seen.add(id(store))
                result.append(store)
        return tuple(result)

    def put(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem):
            raise TypeError("memory_item_required")
        with self._lock:
            self._ensure_open()
            self._backend_for_kind(item.kind).put(item)

    def get(self, memory_id: str, *, execution_id: str | None = None) -> MemoryItem | None:
        with self._lock:
            self._ensure_open()
            matches = [
                item
                for store in self._unique_stores()
                if (item := store.get(memory_id, execution_id=execution_id)) is not None
            ]
            if len(matches) > 1:
                raise RuntimeError("memory_fabric_duplicate_memory_id")
            return matches[0] if matches else None

    def list(self, kind: str | None = None, *, execution_id: str | None = None) -> tuple[MemoryItem, ...]:
        if kind is not None and kind not in self._KINDS:
            return ()
        with self._lock:
            self._ensure_open()
            items = {}
            for store in self._unique_stores():
                for item in store.list(kind, execution_id=execution_id):
                    existing = items.get(item.memory_id)
                    if existing is not None:
                        raise RuntimeError("memory_fabric_duplicate_memory_id")
                    items[item.memory_id] = item
            return tuple(items[key] for key in sorted(items))

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            self._ensure_open()
            matches = [
                store for store in self._unique_stores()
                if store.get(memory_id) is not None
            ]
            if len(matches) > 1:
                raise RuntimeError("memory_fabric_duplicate_memory_id")
            return matches[0].delete(memory_id) if matches else False

    def __len__(self) -> int:
        return len(self.list())

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            for store in self._unique_stores():
                close = getattr(store, "close", None)
                if callable(close):
                    close()
            self._closed = True
