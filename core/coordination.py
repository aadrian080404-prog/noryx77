from dataclasses import dataclass
from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan
from .identity import AgentIdentity


@dataclass(frozen=True)
class AgentAssignment:
    agent_id: str
    task_id: str
    step_id: str


class AgentCoordinator:
    """Coordinates bounded agent execution and only accepts verified results."""
    def __init__(self, router, verifier, max_agents: int = 2):
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or max_agents < 1:
            raise ValueError("max_agents must be a positive integer")
        self.router = router
        self.verifier = verifier
        self.max_agents = max_agents

    def assign(self, plan: Plan) -> tuple[AgentAssignment, ...]:
        if not isinstance(plan, Plan) or not isinstance(plan.task_id, str) or not plan.task_id.strip():
            raise ValueError("invalid_plan")
        if not isinstance(plan.steps, tuple) or not plan.steps:
            raise ValueError("invalid_plan")
        agent_ids = self.router.available()
        if not agent_ids:
            raise LookupError("no agents available")
        assignments = []
        for index, step in enumerate(plan.steps[:self.max_agents]):
            agent_id = agent_ids[index % len(agent_ids)]
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise ValueError("invalid_agent_id")
            if not isinstance(getattr(step, "step_id", None), str) or not step.step_id.strip():
                raise ValueError("invalid_step_id")
            assignments.append(AgentAssignment(agent_id, plan.task_id, step.step_id))
        return tuple(assignments)

    def _trusted_agent(self, agent_id: str):
        try:
            agent = self.router.route(agent_id)
        except LookupError as exc:
            raise LookupError(f"agent_unavailable:{agent_id}") from exc
        if agent is None:
            raise LookupError(f"agent_unavailable:{agent_id}")
        if getattr(agent, "agent_id", None) != agent_id:
            raise RuntimeError(f"agent_identity_mismatch:{agent_id}")
        registry = getattr(self.router, "identity_registry", None)
        if registry is not None:
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or identity.agent_id != agent_id or not registry.is_trusted(identity):
                raise RuntimeError(f"agent_identity_untrusted:{agent_id}")
        return agent

    def execute(self, task: TaskSpec, plan: Plan) -> tuple[AgentResult, ...]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        assignments = self.assign(plan)
        results = []
        for assignment in assignments:
            agent = self._trusted_agent(assignment.agent_id)
            step = next((s for s in plan.steps if s.step_id == assignment.step_id), None)
            if step is None:
                raise ValueError("assignment_step_missing")
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input,
                             task.constraints, task.verification_requirements, step.risk_class)
            child_check = self.verifier.verify_task(child)
            if not isinstance(child_check, VerificationResult) or not child_check.is_well_formed() or not child_check.valid:
                raise RuntimeError(f"child_task_unverified:{assignment.agent_id}")
            result = agent.run(child)
            if not isinstance(result, AgentResult):
                raise RuntimeError(f"invalid_agent_result:{assignment.agent_id}")
            if result.task_id != child.task_id or result.agent_id != assignment.agent_id:
                raise RuntimeError(f"agent_result_identity_mismatch:{assignment.agent_id}")
            if result.status != "completed":
                raise RuntimeError(f"agent_result_incomplete:{assignment.agent_id}")
            if result.verification is None or not result.verification.is_well_formed() or not result.verification.valid:
                raise RuntimeError(f"agent_result_unverified:{assignment.agent_id}")
            if result.verification.stage != "agent_result":
                raise RuntimeError(f"agent_result_verification_stage_mismatch:{assignment.agent_id}")
            output_check = self.verifier.verify_output(result.output, stage="agent_result")
            if not isinstance(output_check, VerificationResult) or not output_check.is_well_formed() or not output_check.valid or output_check.stage != "agent_result":
                raise RuntimeError(f"agent_output_invalid:{assignment.agent_id}")
            results.append(result)
        return tuple(results)

    def verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not isinstance(results, tuple) or not results:
            return VerificationResult(False, "consensus", "no_results")
        if any(not isinstance(r, AgentResult) or not r.is_well_formed() for r in results):
            return VerificationResult(False, "consensus", "malformed_result")
        if any(r.status != "completed" for r in results):
            return VerificationResult(False, "consensus", "incomplete_result")
        if any(r.verification is None or not r.verification.is_well_formed() or not r.verification.valid for r in results):
            return VerificationResult(False, "consensus", "unverified_result")
        if any(r.verification.stage != "agent_result" for r in results):
            return VerificationResult(False, "consensus", "verification_stage_mismatch")
        agent_ids = [r.agent_id for r in results]
        if len(set(agent_ids)) != len(agent_ids):
            return VerificationResult(False, "consensus", "duplicate_agent_identity")
        outputs = [r.output for r in results]
        if any(output != outputs[0] for output in outputs[1:]):
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
