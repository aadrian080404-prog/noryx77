from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    content: Any
    kind: str = "working"
    source: str = ""
    importance: float = 0.0


class MemoryStore:
    """Deterministic bounded store with explicit validation and overwrite semantics."""

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}

    def __init__(self, max_items: int = 10_000):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[str, MemoryItem] = {}

    def put(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not isinstance(item.memory_id, str) or not item.memory_id:
            raise ValueError("valid memory item with memory_id required")
        if item.memory_id not in self._items and len(self._items) >= self.max_items:
            raise MemoryError("memory_capacity_exceeded")
        if item.kind not in self.VALID_KINDS:
            raise ValueError("unsupported memory kind")
        if not isinstance(item.source, str):
            raise ValueError("memory source must be text")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("memory importance must be numeric")
        if not 0.0 <= float(item.importance) <= 1.0:
            raise ValueError("memory importance must be between 0 and 1")
        self._items[item.memory_id] = item

    def get(self, memory_id: str):
        return self._items.get(memory_id) if isinstance(memory_id, str) else None

    def list(self, kind: str | None = None):
        if kind is not None and kind not in self.VALID_KINDS:
            return ()
        return tuple(x for x in self._items.values() if kind is None or x.kind == kind)

    def delete(self, memory_id: str) -> bool:
        if not isinstance(memory_id, str):
            return False
        return self._items.pop(memory_id, None) is not None

    def __len__(self) -> int:
        return len(self._items)
