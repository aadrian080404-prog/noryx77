from __future__ import annotations

from dataclasses import dataclass

from .contracts import TaskSpec


@dataclass(frozen=True)
class AgentContext:
    """Immutable execution context shared across future agent capabilities."""

    runtime_id: str
    execution_id: str
    principal_id: str
    authorization_level: str = "standard"
    capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for name, value in (("runtime_id", self.runtime_id), ("execution_id", self.execution_id), ("principal_id", self.principal_id), ("authorization_level", self.authorization_level)):
            if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 256:
                raise ValueError(f"invalid {name}")
        if not isinstance(self.capabilities, frozenset) or any(not isinstance(item, str) or not item.strip() for item in self.capabilities):
            raise ValueError("invalid capabilities")

    def bind_task(self, task: TaskSpec) -> TaskSpec:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid task")
        if task.execution_id and task.execution_id != self.execution_id:
            raise PermissionError("execution identity mismatch")
        constraints = dict(task.constraints)
        requested_runtime = constraints.get("runtime_id")
        requested_principal = constraints.get("principal_id")
        if requested_runtime not in (None, "", self.runtime_id):
            raise PermissionError("runtime identity mismatch")
        if requested_principal not in (None, "", self.principal_id):
            raise PermissionError("principal identity mismatch")
        constraints["runtime_id"] = self.runtime_id
        constraints["principal_id"] = self.principal_id
        return TaskSpec(task.task_id, task.task_type, task.objective, task.input, constraints, task.verification_requirements, task.risk_class, self.execution_id)
