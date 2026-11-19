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
    """Bounded memory store with exact principal/agent/execution namespaces.

    Empty scope values identify legacy system-global records. Scoped records are
    never returned by an unscoped read. A principal namespace may contain
    principal-wide records (agent_id="") and agent-specific records; reads use
    exact scope matching so an agent cannot implicitly widen its namespace.
    """

    VALID_KINDS = {"working", "local", "edge", "cloud", "long_term", "suspended"}
    MAX_MEMORY_ID_BYTES = 256
    MAX_EXECUTION_ID_BYTES = 256
    MAX_PRINCIPAL_ID_BYTES = 256
    MAX_AGENT_ID_BYTES = 256

    def __init__(self, max_items: int = 10_000):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        self.max_items = max_items
        self._items: dict[tuple[str, str, str, str], MemoryItem] = {}
        self._lock = RLock()

    @staticmethod
    def _valid_scope_id(value: str, maximum: int, *, allow_empty: bool = True) -> bool:
        if not isinstance(value, str):
            return False
        if not allow_empty and not value.strip():
            return False
        return len(value.encode("utf-8")) <= maximum

    @classmethod
    def _valid_execution_id(cls, execution_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            execution_id, cls.MAX_EXECUTION_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_principal_id(cls, principal_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            principal_id, cls.MAX_PRINCIPAL_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_agent_id(cls, agent_id: str, *, allow_empty: bool = True) -> bool:
        return cls._valid_scope_id(
            agent_id, cls.MAX_AGENT_ID_BYTES, allow_empty=allow_empty
        )

    @classmethod
    def _valid_memory_id(cls, memory_id: str) -> bool:
        return (
            isinstance(memory_id, str)
            and bool(memory_id)
            and len(memory_id.encode("utf-8")) <= cls.MAX_MEMORY_ID_BYTES
        )

    @staticmethod
    def _key(memory_id: str, principal_id: str, agent_id: str, execution_id: str):
        return principal_id, agent_id, execution_id, memory_id

    @classmethod
    def _valid_query_scope(cls, principal_id, agent_id, execution_id) -> bool:
        if principal_id is not None and not cls._valid_principal_id(
            principal_id, allow_empty=False
        ):
            return False
        if agent_id is not None and not cls._valid_agent_id(
            agent_id, allow_empty=False
        ):
            return False
        if agent_id is not None and principal_id is None:
            return False
        if execution_id is not None and not cls._valid_execution_id(
            execution_id, allow_empty=False
        ):
            return False
        return True

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
        if item.agent_id and not item.principal_id:
            raise ValueError("agent_scoped_memory_requires_principal")
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
        principal_id: str | None = None,
        agent_id: str | None = None,
        execution_id: str | None = None,
    ):
        if not self._valid_memory_id(memory_id) or not self._valid_query_scope(
            principal_id, agent_id, execution_id
        ):
            return None
        scope = (
            principal_id or "",
            agent_id or "",
            execution_id or "",
            memory_id,
        )
        with self._lock:
            item = self._items.get(scope)
            if item is None:
                return None
            try:
                return deepcopy(item)
            except Exception as exc:
                raise RuntimeError("memory isolation failure") from exc

    def list(
        self,
        kind: str | None = None,
        *,
        principal_id: str | None = None,
        agent_id: str | None = None,
        execution_id: str | None = None,
    ):
        if kind is not None and kind not in self.VALID_KINDS:
            return ()
        if not self._valid_query_scope(principal_id, agent_id, execution_id):
            return ()
        expected = (principal_id or "", agent_id or "", execution_id or "")
        with self._lock:
            try:
                return tuple(
                    deepcopy(item)
                    for (principal, agent, execution, _), item in self._items.items()
                    if (principal, agent, execution) == expected
                    and (kind is None or item.kind == kind)
                )
            except Exception as exc:
                raise RuntimeError("memory isolation failure") from exc

    def delete(
        self,
        memory_id: str,
        *,
        principal_id: str | None = None,
        agent_id: str | None = None,
        execution_id: str | None = None,
    ) -> bool:
        if not self._valid_memory_id(memory_id) or not self._valid_query_scope(
            principal_id, agent_id, execution_id
        ):
            return False
        key = self._key(
            memory_id, principal_id or "", agent_id or "", execution_id or ""
        )
        with self._lock:
            return self._items.pop(key, None) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
