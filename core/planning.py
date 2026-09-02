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
    context_version: int | None = None
    context_source_ids: tuple[str, ...] = ()


class Planner:
    """Deterministic bounded planner; model planners plug in behind this contract."""
    VALID_ACTION_TYPES = {"compute"}
    VALID_RISKS = {"normal", "sensitive", "high"}

    def __init__(self, max_steps: int = 8):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps

    def build(self, task: TaskSpec, context=None) -> Plan:
        if type(task) is not TaskSpec or not task.is_well_formed():
            raise TypeError("task must be a well-formed TaskSpec")
        context_version = None
        context_source_ids = ()
        if context is not None:
            if getattr(context, "task_id", None) != task.task_id:
                raise ValueError("context_task_mismatch")
            context_version = getattr(context, "version", None)
            context_source_ids = getattr(context, "source_ids", ())
            if isinstance(context_version, bool) or not isinstance(context_version, int) or context_version < 1:
                raise ValueError("invalid_context_version")
            if not isinstance(context_source_ids, tuple) or not context_source_ids or context_source_ids[0] != task.task_id:
                raise ValueError("invalid_context_sources")
            if any(not isinstance(source_id, str) or not source_id.strip() for source_id in context_source_ids):
                raise ValueError("invalid_context_sources")
        step = PlanStep(f"{task.task_id}:0", task.objective, "compute", task.risk_class)
        return Plan(task.task_id, (step,), context_version, tuple(context_source_ids))

    def verify(self, plan: Plan, task: TaskSpec, context=None) -> VerificationResult:
        """Independently validate a plan and, when supplied, its context binding."""
        if type(task) is not TaskSpec or not task.is_well_formed():
            return VerificationResult(False, "plan", "invalid_task")
        if type(plan) is not Plan:
            return VerificationResult(False, "plan", "invalid_plan_type")
        if not isinstance(plan.task_id, str) or not plan.task_id.strip() or plan.task_id != task.task_id:
            return VerificationResult(False, "plan", "plan_task_mismatch")
        if not isinstance(plan.steps, tuple) or not plan.steps or len(plan.steps) > self.max_steps:
            return VerificationResult(False, "plan", "plan_bounds_invalid")
        if context is not None:
            if getattr(context, "task_id", None) != task.task_id:
                return VerificationResult(False, "plan", "context_task_mismatch")
            if plan.context_version != getattr(context, "version", None) or plan.context_source_ids != getattr(context, "source_ids", None):
                return VerificationResult(False, "plan", "plan_context_mismatch")
        elif plan.context_version is not None or plan.context_source_ids:
            return VerificationResult(False, "plan", "unexpected_context_binding")

        ids = set()
        prefix = task.task_id + ":"
        for step in plan.steps:
            if type(step) is not PlanStep:
                return VerificationResult(False, "plan", "plan_step_type_invalid")
            if not isinstance(step.step_id, str) or not step.step_id.strip():
                return VerificationResult(False, "plan", "plan_step_id_invalid")
            if not step.step_id.startswith(prefix):
                return VerificationResult(False, "plan", "plan_step_parent_mismatch")
            if step.step_id in ids:
                return VerificationResult(False, "plan", "plan_step_id_invalid")
            if not isinstance(step.objective, str) or not step.objective.strip():
                return VerificationResult(False, "plan", "plan_step_objective_invalid")
            if not isinstance(step.action_type, str) or not step.action_type.strip():
                return VerificationResult(False, "plan", "plan_step_action_invalid")
            if step.action_type not in self.VALID_ACTION_TYPES:
                return VerificationResult(False, "plan", "plan_step_policy_invalid")
            if not isinstance(step.risk_class, str) or not step.risk_class.strip():
                return VerificationResult(False, "plan", "plan_step_risk_invalid")
            if step.risk_class not in self.VALID_RISKS:
                return VerificationResult(False, "plan", "plan_step_policy_invalid")
            if step.risk_class != task.risk_class:
                return VerificationResult(False, "plan", "plan_step_risk_mismatch")
            ids.add(step.step_id)
        return VerificationResult(True, "plan", "plan_ok")
