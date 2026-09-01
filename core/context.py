from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class ContextSnapshot:
    task_id: str
    values: dict[str, Any] = field(default_factory=dict)
    source_ids: tuple[str, ...] = ()
    version: int = 1

class ContextManager:
    """Creates immutable context snapshots instead of mutating agent context."""
    def __init__(self):
        self._versions = {}

    def build(self, task_id, values=None, source_ids=()):
        version = self._versions.get(task_id, 0) + 1
        self._versions[task_id] = version
        return ContextSnapshot(task_id, dict(values or {}), tuple(source_ids), version)
