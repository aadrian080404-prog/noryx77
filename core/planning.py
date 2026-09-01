from dataclasses import dataclass
from .contracts import TaskSpec, VerificationResult

@dataclass(frozen=True)
class PlanStep:
    step_id: str
    objective: str
    action_type: str = "compute"
    risk_class: str = "normal"

@dataclass(frozen=True)
class Plan:
    task_id: str
    steps: tuple[PlanStep, ...]

class Planner:
    """Deterministic bounded planner; future model planners plug in behind this contract."""
    def __init__(self, max_steps: int = 8):
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.max_steps = max_steps

    def build(self, task: TaskSpec) -> Plan:
        if not isinstance(task, TaskSpec):
            raise TypeError("task must be TaskSpec")
        steps = (PlanStep(f"{task.task_id}:0", task.objective, "compute", task.risk_class),)
        return Plan(task.task_id, steps[:self.max_steps])

    def verify(self, plan: Plan, task: TaskSpec) -> VerificationResult:
        if not isinstance(plan, Plan) or plan.task_id != task.task_id:
            return VerificationResult(False, "plan", "plan_task_mismatch")
        if not plan.steps or len(plan.steps) > self.max_steps:
            return VerificationResult(False, "plan", "plan_bounds_invalid")
        for step in plan.steps:
            if not step.objective or step.risk_class != task.risk_class:
                return VerificationResult(False, "plan", "plan_step_invalid")
        return VerificationResult(True, "plan", "plan_ok")
