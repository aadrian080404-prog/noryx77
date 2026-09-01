from dataclasses import dataclass
from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan


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
        if not isinstance(plan, Plan) or not plan.is_well_formed():
            raise ValueError("invalid_plan")
        agents = self.router.available()
        if not agents:
            raise LookupError("no agents available")
        assignments = []
        for index, step in enumerate(plan.steps[:self.max_agents]):
            agent = agents[index % len(agents)]
            agent_id = getattr(agent, "agent_id", None)
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise ValueError("invalid_agent_id")
            assignments.append(AgentAssignment(agent_id, plan.task_id, step.step_id))
        return tuple(assignments)

    def execute(self, task: TaskSpec, plan: Plan) -> tuple[AgentResult, ...]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        assignments = self.assign(plan)
        results = []
        for assignment in assignments:
            agent = self.router.route(assignment.agent_id)
            if agent is None:
                raise LookupError(f"agent_unavailable:{assignment.agent_id}")
            step = next((s for s in plan.steps if s.step_id == assignment.step_id), None)
            if step is None:
                raise ValueError("assignment_step_missing")
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input,
                             task.constraints, task.verification_requirements, step.risk_class)
            result = agent.run(child)
            if not isinstance(result, AgentResult):
                raise RuntimeError(f"invalid_agent_result:{assignment.agent_id}")
            admission = self.verifier.verify_task(child)
            if not admission.valid:
                raise RuntimeError(f"child_task_unverified:{assignment.agent_id}")
            if result.task_id != child.task_id or result.agent_id != assignment.agent_id:
                raise RuntimeError(f"agent_result_identity_mismatch:{assignment.agent_id}")
            if result.verification is None or not result.verification.is_well_formed() or not result.verification.valid:
                raise RuntimeError(f"agent_result_unverified:{assignment.agent_id}")
            output_check = self.verifier.verify_output(result.output, stage="agent_result")
            if not output_check.valid:
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
        outputs = [r.output for r in results]
        if any(output != outputs[0] for output in outputs[1:]):
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
