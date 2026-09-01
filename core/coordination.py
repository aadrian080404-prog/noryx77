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
        self.router = router
        self.verifier = verifier
        self.max_agents = max_agents

    def assign(self, plan: Plan) -> tuple[AgentAssignment, ...]:
        agents = self.router.available()
        if not agents:
            raise LookupError("no agents available")
        assignments = []
        for index, step in enumerate(plan.steps[:self.max_agents]):
            assignments.append(AgentAssignment(agents[index % len(agents)], plan.task_id, step.step_id))
        return tuple(assignments)

    def execute(self, task: TaskSpec, plan: Plan) -> tuple[AgentResult, ...]:
        results = []
        for assignment, step in zip(self.assign(plan), plan.steps):
            agent = self.router.route(assignment.agent_id)
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input,
                             task.constraints, task.verification_requirements, step.risk_class)
            result = agent.run(child)
            if result.verification is None or not result.verification.valid:
                raise RuntimeError(f"agent_result_unverified:{assignment.agent_id}")
            results.append(result)
        return tuple(results)

    def verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not results:
            return VerificationResult(False, "consensus", "no_results")
        if any(r.status != "completed" for r in results):
            return VerificationResult(False, "consensus", "incomplete_result")
        outputs = {repr(r.output) for r in results}
        if len(outputs) > 1:
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
