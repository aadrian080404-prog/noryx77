from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import ExecutionStatus


class LifecycleError(ValueError):
    """Raised when an execution attempts an invalid lifecycle transition."""


_ALLOWED: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.CREATED: frozenset({ExecutionStatus.RUNNING, ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.RUNNING: frozenset({ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.SUCCEEDED: frozenset(),
    ExecutionStatus.REJECTED: frozenset(),
    ExecutionStatus.FAILED: frozenset(),
    ExecutionStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class ExecutionLifecycle:
    """Immutable lifecycle value object enforcing terminal-state semantics."""

    execution_id: str
    principal_id: str
    status: ExecutionStatus = ExecutionStatus.CREATED

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id.strip():
            raise LifecycleError("execution identity required")
        if not isinstance(self.principal_id, str) or not self.principal_id.strip():
            raise LifecycleError("principal identity required")
        if not isinstance(self.status, ExecutionStatus):
            raise LifecycleError("invalid execution status")

    def can_transition(self, target: ExecutionStatus) -> bool:
        return isinstance(target, ExecutionStatus) and target in _ALLOWED[self.status]

    def transition(self, target: ExecutionStatus) -> "ExecutionLifecycle":
        if not self.can_transition(target):
            raise LifecycleError(f"invalid lifecycle transition: {self.status.value}->{getattr(target, 'value', target)}")
        return ExecutionLifecycle(self.execution_id, self.principal_id, target)

    @property
    def terminal(self) -> bool:
        return not _ALLOWED[self.status]
