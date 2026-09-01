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
    """Small deterministic in-process store; persistence/retrieval can be added behind this boundary."""
    def __init__(self):
        self._items: dict[str, MemoryItem] = {}

    def put(self, item: MemoryItem) -> None:
        if not item.memory_id:
            raise ValueError("memory_id required")
        self._items[item.memory_id] = item

    def get(self, memory_id: str):
        return self._items.get(memory_id)

    def list(self, kind: str | None = None):
        values = tuple(self._items.values())
        return tuple(x for x in values if kind is None or x.kind == kind)

    def delete(self, memory_id: str) -> bool:
        return self._items.pop(memory_id, None) is not None
