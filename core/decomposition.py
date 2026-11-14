from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import TaskSpec
from .errors import ContractViolation


@dataclass(frozen=True)
class Subtask:
    subtask_id: str
    objective: str
    task_type: str
    dependencies: tuple[str, ...] = ()


class TaskDecomposer:
    """Deterministic bounded decomposition with an explicit structured-subtask contract."""

    def __init__(self, max_subtasks: int = 8):
        if isinstance(max_subtasks, bool) or not isinstance(max_subtasks, int) or max_subtasks < 1:
            raise ValueError("max_subtasks must be a positive integer")
        self.max_subtasks = max_subtasks

    def decompose(self, task: TaskSpec) -> tuple[Subtask, ...]:
        if not isinstance(task, TaskSpec) or not task.task_id or not task.objective:
            raise ContractViolation("task_id and objective are required")
        raw = task.constraints.get("subtasks") if isinstance(task.constraints, Mapping) else None
        if raw is None:
            return (Subtask(task.task_id + ":0", task.objective, task.task_type),)
        if not isinstance(raw, (tuple, list)) or not raw:
            raise ContractViolation("subtasks must be a non-empty sequence")
        if len(raw) > self.max_subtasks:
            raise ContractViolation("subtask_bound_exceeded")

        subtasks: list[Subtask] = []
        for index, item in enumerate(raw):
            if isinstance(item, str):
                objective = item
                dependencies: tuple[str, ...] = ()
            elif isinstance(item, Mapping):
                objective = item.get("objective", "")
                raw_dependencies = item.get("dependencies", ())
                if not isinstance(raw_dependencies, (tuple, list)):
                    raise ContractViolation("subtask_dependencies_invalid")
                dependencies = tuple(str(dep) for dep in raw_dependencies)
            else:
                raise ContractViolation("subtask_definition_invalid")
            if not isinstance(objective, str) or not objective.strip():
                raise ContractViolation("subtask_objective_required")
            if any(not dep.strip() for dep in dependencies):
                raise ContractViolation("subtask_dependency_invalid")
            normalized_dependencies = tuple(
                dep if dep.startswith(task.task_id + ":") else task.task_id + ":" + dep
                for dep in dependencies
            )
            subtasks.append(Subtask(task.task_id + ":" + str(index), objective.strip(), task.task_type, normalized_dependencies))

        known = {item.subtask_id for item in subtasks}
        for item in subtasks:
            if item.subtask_id in item.dependencies:
                raise ContractViolation("subtask_self_dependency")
            if any(dep not in known for dep in item.dependencies):
                raise ContractViolation("subtask_dependency_unknown")
            if any(int(dep.rsplit(":", 1)[1]) >= int(item.subtask_id.rsplit(":", 1)[1]) for dep in item.dependencies):
                raise ContractViolation("subtask_dependency_order_invalid")
        return tuple(subtasks)
