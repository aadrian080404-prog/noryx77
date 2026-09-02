from .contracts import AgentResult, TaskSpec
from .provider import Provider, request_from_task
from .verification import VerificationEngine


class Agent:
    agent_id = "base"
    model_class = "medium"
    capabilities = ()

    def run(self, task: TaskSpec) -> AgentResult:
        raise NotImplementedError


class DeterministicAgent(Agent):
    agent_id = "deterministic"
    model_class = "micro"
    capabilities = ("deterministic",)

    def __init__(self, verifier: VerificationEngine | None = None):
        self.verifier = verifier or VerificationEngine()

    def run(self, task: TaskSpec) -> AgentResult:
        check = self.verifier.verify_task(task)
        if not check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        result = AgentResult(self.agent_id, task.task_id, "completed", output=task.objective)
        output_check = self.verifier.verify_output(result.output, requirements=task.verification_requirements, stage="result")
        return AgentResult(self.agent_id, task.task_id, result.status, result.output, output_check)


class ProviderAgent(Agent):
    """Executes a task through an injected Provider and exposes routing metadata."""

    def __init__(self, agent_id: str, provider: Provider, verifier: VerificationEngine | None = None, *, model_class: str = "medium", capabilities: tuple[str, ...] = ()):
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id_required")
        if not callable(getattr(provider, "execute", None)):
            raise TypeError("provider_execute_required")
        if model_class not in ("micro", "small", "medium", "large", "frontier"):
            raise ValueError("invalid_model_class")
        if not isinstance(capabilities, tuple) or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("invalid_capabilities")
        self.agent_id = agent_id
        self.provider = provider
        self.verifier = verifier or VerificationEngine()
        self.model_class = model_class
        self.capabilities = capabilities
        self.provider_id = getattr(provider, "provider_id", "")
        self.model_id = getattr(provider, "model_id", "")

    def run(self, task: TaskSpec) -> AgentResult:
        task_check = self.verifier.verify_task(task)
        if not task_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=task_check)
        try:
            response = self.provider.execute(request_from_task(task))
        except Exception:
            check = VerificationEngine().verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if getattr(response, "provider_id", None) != getattr(self.provider, "provider_id", None):
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        output = getattr(response, "output", None)
        output_check = self.verifier.verify_output(output, requirements=task.verification_requirements, stage="result")
        if not output_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", output, output_check)
        return AgentResult(self.agent_id, task.task_id, "completed", output, output_check)


__all__ = ["Agent", "DeterministicAgent", "ProviderAgent"]
