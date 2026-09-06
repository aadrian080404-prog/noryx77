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
    """Deterministic bounded store with explicit execution-scoped identity."""

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}
    MAX_EXECUTION_ID_BYTES = 256

    def __init__(self, max_items: int = 10_000):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[tuple[str, str], MemoryItem] = {}

    @classmethod
    def _valid_execution_id(cls, execution_id: str, *, allow_empty: bool = True) -> bool:
        if not isinstance(execution_id, str): return False
        if not allow_empty and not execution_id.strip(): return False
        return len(execution_id.encode("utf-8")) <= cls.MAX_EXECUTION_ID_BYTES

    @staticmethod
    def _key(memory_id: str, execution_id: str) -> tuple[str, str]:
        return (execution_id, memory_id)

    def _validate_item(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not isinstance(item.memory_id, str) or not item.memory_id:
            raise ValueError("valid memory item with memory_id required")
        if item.kind not in self.VALID_KINDS: raise ValueError("unsupported memory kind")
        if not isinstance(item.source, str): raise ValueError("memory source must be text")
        if not self._valid_execution_id(item.execution_id): raise ValueError("invalid memory execution identity")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)): raise ValueError("memory importance must be numeric")
        if not 0.0 <= float(item.importance) <= 1.0: raise ValueError("memory importance must be between 0 and 1")

    def put(self, item_or_id, content=None, *, execution_id: str | None = None) -> None:
        if isinstance(item_or_id, MemoryItem):
            if content is not None or execution_id is not None: raise TypeError("MemoryItem form does not accept content or execution_id")
            item = item_or_id
        else:
            if not isinstance(item_or_id, str) or not item_or_id: raise ValueError("valid memory item with memory_id required")
            item = MemoryItem(item_or_id, content, execution_id=execution_id or "")
        self._validate_item(item)
        key = self._key(item.memory_id, item.execution_id)
        if key not in self._items and len(self._items) >= self.max_items: raise MemoryError("memory_capacity_exceeded")
        try: isolated = deepcopy(item)
        except Exception as exc: raise ValueError("memory content must be copyable") from exc
        self._items[key] = isolated

    def get(self, memory_id: str, *, execution_id: str | None = None):
        if not isinstance(memory_id, str): return None
        if execution_id is not None:
            if not self._valid_execution_id(execution_id, allow_empty=False): return None
            item = self._items.get(self._key(memory_id, execution_id))
        else:
            item = self._items.get(self._key(memory_id, ""))
        if item is None: return None
        try: return deepcopy(item)
        except Exception as exc: raise RuntimeError("memory isolation failure") from exc

    def list(self, kind: str | None = None, *, execution_id: str | None = None):
        if kind is not None and kind not in self.VALID_KINDS: return ()
        if execution_id is not None and not self._valid_execution_id(execution_id, allow_empty=False): return ()
        try:
            return tuple(deepcopy(x) for x in self._items.values() if (kind is None or x.kind == kind) and (execution_id is None or x.execution_id == execution_id))
        except Exception as exc: raise RuntimeError("memory isolation failure") from exc

    def delete(self, memory_id: str, *, execution_id: str | None = None) -> bool:
        if not isinstance(memory_id, str): return False
        if execution_id is not None:
            if not self._valid_execution_id(execution_id, allow_empty=False): return False
            key = self._key(memory_id, execution_id)
        else:
            key = self._key(memory_id, "")
        item = self._items.get(key)
        if item is None: return False
        if item.execution_id and execution_id != item.execution_id: return False
        del self._items[key]
        return True

    def __len__(self) -> int: return len(self._items)
