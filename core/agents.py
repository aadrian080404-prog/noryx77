from copy import deepcopy
from collections.abc import Mapping

from .contracts import AgentResult, TaskSpec
from .provider import Provider, ProviderResponse, request_from_task
from .verification import VerificationEngine


class Agent:
    agent_id = "base"
    model_class = "medium"
    capabilities = ()
    capacity_exempt = False

    def run(self, task: TaskSpec) -> AgentResult:
        raise NotImplementedError


class DeterministicAgent(Agent):
    agent_id = "deterministic"
    model_class = "micro"
    capabilities = ("deterministic",)
    capacity_exempt = True

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

    @staticmethod
    def _callable_fingerprint(callable_obj):
        function = getattr(callable_obj, "__func__", None)
        owner = getattr(callable_obj, "__self__", None)
        return (id(function if function is not None else callable_obj), id(owner) if owner is not None else None)

    def __init__(self, agent_id: str, provider: Provider, verifier: VerificationEngine | None = None, *, model_class: str = "medium", capabilities: tuple[str, ...] = ()):
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id_required")
        if not callable(getattr(provider, "execute", None)):
            raise TypeError("provider_execute_required")
        provider_id = getattr(provider, "provider_id", "")
        model_id = getattr(provider, "model_id", "")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id_required")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id_required")
        if model_class not in ("micro", "small", "medium", "large", "frontier"):
            raise ValueError("invalid_model_class")
        if not isinstance(capabilities, tuple) or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("invalid_capabilities")
        self.agent_id = agent_id
        self.provider = provider
        self.verifier = verifier or VerificationEngine()
        self.model_class = model_class
        self.capabilities = capabilities
        self.capacity_exempt = False
        self.provider_id = provider_id
        self.model_id = model_id
        self._provider_execute_fingerprint = self._callable_fingerprint(provider.execute)

    def run(self, task: TaskSpec) -> AgentResult:
        task_check = self.verifier.verify_task(task)
        if not task_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=task_check)

        expected_provider = self.provider
        expected_provider_id = self.provider_id
        expected_model_id = self.model_id
        try:
            current_execute = expected_provider.execute
            if self._callable_fingerprint(current_execute) != self._provider_execute_fingerprint:
                check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
                return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
            expected_execute = current_execute
            response = expected_execute(request_from_task(task))
        except Exception:
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if self.provider is not expected_provider or self.provider_id != expected_provider_id or self.model_id != expected_model_id:
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if not isinstance(response, ProviderResponse):
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if not isinstance(response.provider_id, str) or not response.provider_id.strip():
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if response.provider_id != expected_provider_id:
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if not isinstance(response.model_id, str) or not response.model_id.strip() or response.model_id != expected_model_id:
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        if response.metadata is not None and not isinstance(response.metadata, Mapping):
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        try:
            isolated_output = deepcopy(response.output)
        except Exception:
            check = self.verifier.verify_output(None, requirements=task.verification_requirements, stage="result")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check)
        output_check = self.verifier.verify_output(isolated_output, requirements=task.verification_requirements, stage="result")
        if not output_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", isolated_output, output_check)
        return AgentResult(self.agent_id, task.task_id, "completed", isolated_output, output_check)


__all__ = ["Agent", "DeterministicAgent", "ProviderAgent"]
