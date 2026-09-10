from dataclasses import dataclass
from typing import Any, Mapping

from .capability_fabric import CapabilityFabric
from .contracts import TaskSpec, VerificationResult


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    objective: str
    action_type: str = "compute"
    risk_class: str = "normal"
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    task_id: str
    steps: tuple[PlanStep, ...]


class Planner:
    """Deterministic bounded planner with one canonical capability-selection boundary."""
    VALID_ACTION_TYPES = {"compute", "agent_collaboration", "web_research", "chess_analyze", "payments", "flights", "insurance", "contracts", "bureaucracy"}
    VALID_RISKS = {"normal", "sensitive", "high"}

    def __init__(self, max_steps: int = 8, *, collaboration_enabled: bool = False, capability_fabric: CapabilityFabric | None = None):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        if not isinstance(collaboration_enabled, bool):
            raise ValueError("collaboration_enabled must be bool")
        self.max_steps = max_steps
        self.collaboration_enabled = collaboration_enabled
        self.capability_fabric = capability_fabric or CapabilityFabric()

    @staticmethod
    def _risk_for_capability(intent, task_risk: str) -> str:
        if intent.risk_class == "high":
            return "high"
        if intent.risk_class == "sensitive" and task_risk == "normal":
            return "sensitive"
        return task_risk

    def _action_for(self, task: TaskSpec, objective: str) -> tuple[str, str]:
        intent = self.capability_fabric.classify(f"{task.objective}\n{task.input}\n{objective}", explicit_capability=task.task_type if task.task_type in self.VALID_ACTION_TYPES and task.task_type != "compute" else None)
        if intent.capability != "compute":
            return intent.capability, self._risk_for_capability(intent, task.risk_class)
        if self.collaboration_enabled:
            return "agent_collaboration", task.risk_class
        return "compute", task.risk_class

    def build(self, task: TaskSpec) -> Plan:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise TypeError("task must be a well-formed TaskSpec")
        raw = task.constraints.get("subtasks") if isinstance(task.constraints, Mapping) else None
        if raw is not None:
            if not isinstance(raw, (tuple, list)) or not raw or len(raw) > self.max_steps:
                raise ValueError("subtasks exceed planner bounds")
            steps = []
            for index, item in enumerate(raw):
                if isinstance(item, str):
                    objective, dependencies = item, ()
                elif isinstance(item, Mapping):
                    objective = item.get("objective", "")
                    raw_dependencies = item.get("dependencies", ())
                    if not isinstance(raw_dependencies, (tuple, list)):
                        raise ValueError("subtask dependencies invalid")
                    dependencies = tuple(dep if str(dep).startswith(task.task_id + ":") else task.task_id + ":" + str(dep) for dep in raw_dependencies)
                else:
                    raise ValueError("subtask definition invalid")
                if not isinstance(objective, str) or not objective.strip():
                    raise ValueError("subtask objective required")
                action_type, risk_class = self._action_for(task, objective.strip())
                steps.append(PlanStep(f"{task.task_id}:{index}", objective.strip(), action_type, risk_class, dependencies))
            return Plan(task.task_id, tuple(steps))

        action_type, risk_class = self._action_for(task, task.objective)
        return Plan(task.task_id, (PlanStep(f"{task.task_id}:0", task.objective, action_type, risk_class),))

    def verify(self, plan: Plan, task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "plan", "invalid_task")
        if not isinstance(plan, Plan) or not isinstance(plan.task_id, str) or plan.task_id != task.task_id:
            return VerificationResult(False, "plan", "plan_task_mismatch")
        if not isinstance(plan.steps, tuple) or not plan.steps or len(plan.steps) > self.max_steps:
            return VerificationResult(False, "plan", "plan_bounds_invalid")
        ids = set()
        for index, step in enumerate(plan.steps):
            if not isinstance(step, PlanStep):
                return VerificationResult(False, "plan", "plan_step_type_invalid")
            if not isinstance(step.step_id, str) or not step.step_id or step.step_id in ids:
                return VerificationResult(False, "plan", "plan_step_id_invalid")
            ids.add(step.step_id)
            if not isinstance(step.objective, str) or not step.objective.strip():
                return VerificationResult(False, "plan", "plan_step_objective_invalid")
            if step.action_type not in self.VALID_ACTION_TYPES or step.risk_class not in self.VALID_RISKS:
                return VerificationResult(False, "plan", "plan_step_policy_invalid")
            if step.risk_class != task.risk_class and step.risk_class != "high":
                return VerificationResult(False, "plan", "plan_step_risk_mismatch")
            if not isinstance(step.dependencies, tuple) or any(not isinstance(dep, str) or not dep for dep in step.dependencies):
                return VerificationResult(False, "plan", "plan_step_dependencies_invalid")
            if any(dep == step.step_id or dep not in ids for dep in step.dependencies):
                return VerificationResult(False, "plan", "plan_step_dependency_invalid")
        return VerificationResult(True, "plan", "plan_ok")
