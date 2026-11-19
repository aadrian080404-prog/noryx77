from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    content: Any
    kind: str = "working"
    source: str = ""
    importance: float = 0.0
    execution_id: str = ""
    principal_id: str = ""
    agent_id: str = ""


class MemoryStore:
    """Deterministic bounded store with exact principal/agent/execution isolation.

    Empty identity fields denote explicitly global/system memory. Scoped records
    are never returned by an unscoped read, and every identity dimension on a
    record must match the corresponding read context exactly.
    """

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}
    MAX_MEMORY_ID_BYTES = 256
    MAX_EXECUTION_ID_BYTES = 256
    MAX_PRINCIPAL_ID_BYTES = 1024
    MAX_AGENT_ID_BYTES = 1024

    def __init__(self, max_items: int = 10_000):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[tuple[str, str, str, str], MemoryItem] = {}
        self._lock = RLock()

    @classmethod
    def _valid_scope_id(cls, value: str, *, max_bytes: int, allow_empty: bool = True) -> bool:
        if not isinstance(value, str):
            return False
        if not allow_empty and not value.strip():
            return False
        return len(value.encode("utf-8")) <= max_bytes

    @classmethod
    def _valid_execution_id(cls, execution_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            execution_id, max_bytes=cls.MAX_EXECUTION_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_principal_id(cls, principal_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            principal_id, max_bytes=cls.MAX_PRINCIPAL_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_agent_id(cls, agent_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            agent_id, max_bytes=cls.MAX_AGENT_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_memory_id(cls, memory_id: str) -> bool:
        return isinstance(memory_id, str) and bool(memory_id) and len(memory_id.encode("utf-8")) <= cls.MAX_MEMORY_ID_BYTES

    @staticmethod
    def _key(memory_id: str, principal_id: str, agent_id: str, execution_id: str):
        return memory_id, principal_id, agent_id, execution_id

    @staticmethod
    def _matches_scope(item: MemoryItem, *, principal_id: str, agent_id: str, execution_id: str) -> bool:
        return (
            item.principal_id == principal_id
            and item.agent_id == agent_id
            and item.execution_id == execution_id
        )

    def put(self, item: MemoryItem) -> None:
        if not isinstance(item, MemoryItem) or not self._valid_memory_id(item.memory_id):
            raise ValueError("valid memory item with memory_id required")
        if item.kind not in self.VALID_KINDS:
            raise ValueError("unsupported memory kind")
        if not isinstance(item.source, str):
            raise ValueError("memory source must be text")
        if not self._valid_execution_id(item.execution_id):
            raise ValueError("invalid memory execution identity")
        if not self._valid_principal_id(item.principal_id):
            raise ValueError("invalid memory principal identity")
        if not self._valid_agent_id(item.agent_id):
            raise ValueError("invalid memory agent identity")
        if isinstance(item.importance, bool) or not isinstance(item.importance, (int, float)):
            raise ValueError("memory importance must be numeric")
        if not isfinite(float(item.importance)) or not 0.0 <= float(item.importance) <= 1.0:
            raise ValueError("memory importance must be between 0 and 1")
        try:
            isolated = deepcopy(item)
        except Exception as exc:
            raise ValueError("memory content must be copyable") from exc
        key = self._key(item.memory_id, item.principal_id, item.agent_id, item.execution_id)
        with self._lock:
            if key not in self._items and len(self._items) >= self.max_items:
                raise MemoryError("memory_capacity_exceeded")
            self._items[key] = isolated

    def get(
        self,
        memory_id: str,
        *,
        principal_id: str = "",
        agent_id: str = "",
        execution_id: str | None = None,
    ):
        if execution_id is None:
            execution_id = ""
        if not self._valid_memory_id(memory_id):
            return None
        if (
            not self._valid_principal_id(principal_id)
            or not self._valid_agent_id(agent_id)
            or not self._valid_execution_id(execution_id)
        ):
            return None
        key = self._key(memory_id, principal_id, agent_id, execution_id)
        with self._lock:
            item = self._items.get(key)
            if item is None or not self._matches_scope(
                item, principal_id=principal_id, agent_id=agent_id, execution_id=execution_id
            ):
                return None
            try:
                return deepcopy(item)
            except Exception as exc:
                raise RuntimeError("memory isolation failure") from exc

    def list(
        self,
        kind: str | None = None,
        *,
        principal_id: str = "",
        agent_id: str = "",
        execution_id: str | None = None,
    ):
        if execution_id is None:
            execution_id = ""
        if kind is not None and kind not in self.VALID_KINDS:
            return ()
        if (
            not self._valid_principal_id(principal_id)
            or not self._valid_agent_id(agent_id)
            or not self._valid_execution_id(execution_id)
        ):
            return ()
        with self._lock:
            try:
                return tuple(
                    deepcopy(item)
                    for item in self._items.values()
                    if (kind is None or item.kind == kind)
                    and self._matches_scope(
                        item, principal_id=principal_id, agent_id=agent_id, execution_id=execution_id
                    )
                )
            except Exception as exc:
                raise RuntimeError("memory isolation failure") from exc

    def delete(
        self,
        memory_id: str,
        *,
        principal_id: str = "",
        agent_id: str = "",
        execution_id: str = "",
    ) -> bool:
        if not self._valid_memory_id(memory_id):
            return False
        if (
            not self._valid_principal_id(principal_id)
            or not self._valid_agent_id(agent_id)
            or not self._valid_execution_id(execution_id)
        ):
            return False
        key = self._key(memory_id, principal_id, agent_id, execution_id)
        with self._lock:
            return self._items.pop(key, None) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
