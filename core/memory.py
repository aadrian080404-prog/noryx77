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
    """Deterministic bounded store with explicit overwrite/delete semantics."""

    def __init__(self, max_items: int = 10_000):
        if not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[str, MemoryItem] = {}

    def put(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not item.memory_id:
            raise ValueError("valid memory item with memory_id required")
        if item.memory_id not in self._items and len(self._items) >= self.max_items:
            raise MemoryError("memory_capacity_exceeded")
        if not isinstance(item.kind, str) or not item.kind:
            raise ValueError("memory kind required")
        if not isinstance(item.source, str):
            raise ValueError("memory source must be text")
        if not isinstance(item.importance, (int, float)) or not 0.0 <= float(item.importance) <= 1.0:
            raise ValueError("memory importance must be between 0 and 1")
        self._items[item.memory_id] = item

    def get(self, memory_id: str):
        if not isinstance(memory_id, str):
            return None
        return self._items.get(memory_id)

    def list(self, kind: str | None = None):
        values = tuple(self._items.values())
        return tuple(x for x in values if kind is None or x.kind == kind)

    def delete(self, memory_id: str) -> bool:
        if not isinstance(memory_id, str):
            return False
        return self._items.pop(memory_id, None) is not None

    def __len__(self) -> int:
        return len(self._items)
