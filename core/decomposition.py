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
        if not task.task_id or not task.objective:
            raise ContractViolation("task_id and objective are required")
        return (Subtask(task.task_id + ":0", task.objective, task.task_type),)
