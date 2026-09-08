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
    """Deterministic bounded planner; model planners plug in behind this contract."""
    VALID_ACTION_TYPES = {"compute", "agent_collaboration", "web_research", "chess_analyze", "payments", "flights", "insurance"}
    VALID_RISKS = {"normal", "sensitive", "high"}

    def __init__(self, max_steps: int = 8, *, collaboration_enabled: bool = False):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        if not isinstance(collaboration_enabled, bool):
            raise ValueError("collaboration_enabled must be bool")
        self.max_steps = max_steps
        self.collaboration_enabled = collaboration_enabled

    def build(self, task: TaskSpec) -> Plan:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise TypeError("task must be a well-formed TaskSpec")
        frontier = {"web_research", "chess_analyze", "payments", "flights", "insurance"}
        if task.task_type in frontier:
            action_type = task.task_type
        elif self.collaboration_enabled:
            action_type = "agent_collaboration"
        else:
            action_type = "compute"
        step = PlanStep(f"{task.task_id}:0", task.objective, action_type, task.risk_class)
        return Plan(task.task_id, (step,))

    def verify(self, plan: Plan, task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "plan", "invalid_task")
        if not isinstance(plan, Plan) or not isinstance(plan.task_id, str) or plan.task_id != task.task_id:
            return VerificationResult(False, "plan", "plan_task_mismatch")
        if not isinstance(plan.steps, tuple) or not plan.steps or len(plan.steps) > self.max_steps:
            return VerificationResult(False, "plan", "plan_bounds_invalid")
        ids = set()
        for step in plan.steps:
            if not isinstance(step, PlanStep):
                return VerificationResult(False, "plan", "plan_step_type_invalid")
            if not isinstance(step.step_id, str) or not step.step_id or step.step_id in ids:
                return VerificationResult(False, "plan", "plan_step_id_invalid")
            ids.add(step.step_id)
            if not isinstance(step.objective, str) or not step.objective.strip():
                return VerificationResult(False, "plan", "plan_step_objective_invalid")
            if step.action_type not in self.VALID_ACTION_TYPES or step.risk_class not in self.VALID_RISKS:
                return VerificationResult(False, "plan", "plan_step_policy_invalid")
            if step.risk_class != task.risk_class:
                return VerificationResult(False, "plan", "plan_step_risk_mismatch")
        return VerificationResult(True, "plan", "plan_ok")
