from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    content: Any
    kind: str = "working"
    source: str = ""
    importance: float = 0.0


class MemoryStore:
    """Deterministic bounded store with isolation and authenticated entries."""

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}

    def __init__(self, max_items: int = 10_000, crypto: CryptoIntegrity | None = None):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[str, MemoryItem] = {}
        self._auth: dict[str, str] = {}
        self._crypto = crypto or CryptoIntegrity()

    @staticmethod
    def _payload(item: MemoryItem) -> dict[str, Any]:
        return {
            "memory_id": item.memory_id,
            "content": deepcopy(item.content),
            "kind": item.kind,
            "source": item.source,
            "importance": float(item.importance),
        }

    def _validate(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not isinstance(item.memory_id, str) or not item.memory_id.strip():
            raise ValueError("valid memory item with memory_id required")
        if item.kind not in self.VALID_KINDS:
            raise ValueError("unsupported memory kind")
        if not isinstance(item.source, str):
            raise ValueError("memory source must be text")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("memory importance must be numeric")
        if not 0.0 <= float(item.importance) <= 1.0:
            raise ValueError("memory importance must be between 0 and 1")

    def _integrity_ok(self, memory_id: str, item: MemoryItem) -> bool:
        tag = self._auth.get(memory_id)
        return self._crypto.verify_digest("memory", self._payload(item), tag)

    def put(self, item: MemoryItem) -> None:
        self._validate(item)
        if item.memory_id not in self._items and len(self._items) >= self.max_items:
            raise MemoryError("memory_capacity_exceeded")
        stored = deepcopy(item)
        self._items[item.memory_id] = stored
        self._auth[item.memory_id] = self._crypto.digest("memory", self._payload(stored))

    def get(self, memory_id: str):
        item = self._items.get(memory_id) if isinstance(memory_id, str) else None
        if item is None:
            return None
        if not self._integrity_ok(memory_id, item):
            raise MemoryError("memory_integrity_failure")
        return deepcopy(item)

    def list(self, kind: str | None = None):
        if kind is not None and kind not in self.VALID_KINDS:
            return ()
        result = []
        for memory_id, item in self._items.items():
            if not self._integrity_ok(memory_id, item):
                raise MemoryError("memory_integrity_failure")
            if kind is None or item.kind == kind:
                result.append(deepcopy(item))
        return tuple(result)

    def delete(self, memory_id: str) -> bool:
        if not isinstance(memory_id, str):
            return False
        removed = self._items.pop(memory_id, None)
        self._auth.pop(memory_id, None)
        return removed is not None

    def __len__(self) -> int:
        return len(self._items)
