from dataclasses import dataclass

from .contracts import TaskSpec
from .errors import ContractViolation


@dataclass(frozen=True)
class Subtask:
    subtask_id: str
    objective: str
    task_type: str


class TaskDecomposer:
    """Conservative decomposition: one validated task becomes one bounded subtask by default."""

    def decompose(self, task: TaskSpec) -> tuple[Subtask, ...]:
        """Produce only subtasks that are structurally bound to the validated parent task."""
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ContractViolation("task must be a well-formed TaskSpec")

        subtask = Subtask(
            subtask_id=f"{task.task_id}:0",
            objective=task.objective,
            task_type=task.task_type,
        )

        if (
            not isinstance(subtask.subtask_id, str)
            or not subtask.subtask_id.strip()
            or not subtask.subtask_id.startswith(task.task_id + ":")
            or not isinstance(subtask.objective, str)
            or not subtask.objective.strip()
            or subtask.objective != task.objective
            or not isinstance(subtask.task_type, str)
            or not subtask.task_type.strip()
            or subtask.task_type != task.task_type
        ):
            raise ContractViolation("decomposition_identity_mismatch")

        return (subtask,)
