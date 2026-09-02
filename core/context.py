from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContextSnapshot:
    task_id: str
    values: dict[str, Any] = field(default_factory=dict)
    source_ids: tuple[str, ...] = ()
    version: int = 1


class ContextManager:
    """Build immutable context snapshots with optional authenticated memory retrieval."""

    def __init__(self, memory=None, *, memory_limit: int = 8):
        if memory_limit is not None and (isinstance(memory_limit, bool) or not isinstance(memory_limit, int) or memory_limit < 1):
            raise ValueError("memory_limit must be a positive integer")
        self._versions = {}
        self._memory = memory
        self._memory_limit = memory_limit

    def attach_memory(self, memory, *, memory_limit: int | None = None) -> None:
        if memory is None or not callable(getattr(memory, "retrieve", None)):
            raise TypeError("memory_retrieve_required")
        if memory_limit is not None and (isinstance(memory_limit, bool) or not isinstance(memory_limit, int) or memory_limit < 1):
            raise ValueError("memory_limit must be a positive integer")
        self._memory = memory
        if memory_limit is not None:
            self._memory_limit = memory_limit

    def build(self, task_id, values=None, source_ids=()):
        version = self._versions.get(task_id, 0) + 1
        self._versions[task_id] = version
        snapshot_values = deepcopy(values or {})
        if self._memory is not None:
            memories = self._memory.retrieve(limit=self._memory_limit)
            snapshot_values["memory"] = tuple(deepcopy(item) for item in memories)
            source_ids = tuple(source_ids) + tuple(item.memory_id for item in memories)
        return ContextSnapshot(task_id, snapshot_values, tuple(source_ids), version)
