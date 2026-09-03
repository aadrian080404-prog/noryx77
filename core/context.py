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
    """Creates context snapshots isolated from caller-owned mutable data."""
    def __init__(self):
        self._versions = {}

    def build(self, task_id, values=None, source_ids=()):
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id required")
        if values is not None and not isinstance(values, dict):
            raise ValueError("values must be a dict")
        if not isinstance(source_ids, tuple):
            raise ValueError("source_ids must be a tuple")
        if any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):
            raise ValueError("source_ids must contain non-empty strings")
        version = self._versions.get(task_id, 0) + 1
        self._versions[task_id] = version
        return ContextSnapshot(task_id, deepcopy(values or {}), tuple(source_ids), version)
