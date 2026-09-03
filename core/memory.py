from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    content: Any
    kind: str = "working"
    source: str = ""
    importance: float = 0.0
    execution_id: str = ""


class MemoryStore:
    """Deterministic bounded store with explicit validation and execution isolation."""

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}
    MAX_EXECUTION_ID_BYTES = 256

    def __init__(self, max_items: int = 10_000):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[str, MemoryItem] = {}

    @classmethod
    def _valid_execution_id(cls, execution_id: str, *, allow_empty: bool = True) -> bool:
        if not isinstance(execution_id, str):
            return False
        if not allow_empty and not execution_id.strip():
            return False
        return len(execution_id.encode("utf-8")) <= cls.MAX_EXECUTION_ID_BYTES

    def put(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not isinstance(item.memory_id, str) or not item.memory_id:
            raise ValueError("valid memory item with memory_id required")
        if item.memory_id not in self._items and len(self._items) >= self.max_items:
            raise MemoryError("memory_capacity_exceeded")
        if item.kind not in self.VALID_KINDS:
            raise ValueError("unsupported memory kind")
        if not isinstance(item.source, str):
            raise ValueError("memory source must be text")
        if not self._valid_execution_id(item.execution_id):
            raise ValueError("invalid memory execution identity")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("memory importance must be numeric")
        if not 0.0 <= float(item.importance) <= 1.0:
            raise ValueError("memory importance must be between 0 and 1")
        try:
            isolated = deepcopy(item)
        except Exception as exc:
            raise ValueError("memory content must be copyable") from exc
        self._items[item.memory_id] = isolated

    def get(self, memory_id: str, *, execution_id: str | None = None):
        if not isinstance(memory_id, str):
            return None
        item = self._items.get(memory_id)
        if item is None:
            return None
        if execution_id is not None:
            if not self._valid_execution_id(execution_id, allow_empty=False):
                return None
            if not item.execution_id or item.execution_id != execution_id:
                return None
        try:
            return deepcopy(item)
        except Exception as exc:
            raise RuntimeError("memory isolation failure") from exc

    def list(self, kind: str | None = None, *, execution_id: str | None = None):
        if kind is not None and kind not in self.VALID_KINDS:
            return ()
        if execution_id is not None and not self._valid_execution_id(execution_id, allow_empty=False):
            return ()
        try:
            return tuple(
                deepcopy(x)
                for x in self._items.values()
                if (kind is None or x.kind == kind)
                and (execution_id is None or x.execution_id == execution_id)
                and (execution_id is None or bool(x.execution_id))
            )
        except Exception as exc:
            raise RuntimeError("memory isolation failure") from exc

    def delete(self, memory_id: str) -> bool:
        if not isinstance(memory_id, str):
            return False
        return self._items.pop(memory_id, None) is not None

    def __len__(self) -> int:
        return len(self._items)
