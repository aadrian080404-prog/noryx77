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
    """Creates isolated context snapshots and optionally hydrates prior task memory."""
    def __init__(self, memory=None):
        self._versions = {}
        self.memory = memory

    def _memory_values(self, task_id, limit=16):
        if self.memory is None:
            return ()
        try:
            items = self.memory.list()
        except Exception:
            return ()
        matches = [item for item in items if item.source == task_id]
        matches.sort(key=lambda item: (-float(item.importance), item.memory_id))
        return tuple({
            "memory_id": item.memory_id,
            "kind": item.kind,
            "content": deepcopy(item.content),
            "execution_id": item.execution_id,
        } for item in matches[:limit])

    def build(self, task_id, values=None, source_ids=(), *, execution_id=None):
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id required")
        if values is not None and not isinstance(values, dict):
            raise ValueError("values must be a dict")
        if not isinstance(source_ids, tuple):
            raise ValueError("source_ids must be a tuple")
        if any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):
            raise ValueError("source_ids must contain non-empty strings")
        if execution_id is not None and (not isinstance(execution_id, str) or not execution_id.strip()):
            raise ValueError("execution_id must be a non-empty string when provided")
        version = self._versions.get(task_id, 0) + 1
        self._versions[task_id] = version
        hydrated = deepcopy(values or {})
        prior_memory = self._memory_values(task_id)
        if prior_memory:
            hydrated["memory"] = prior_memory
        return ContextSnapshot(task_id, hydrated, tuple(source_ids), version)
