from copy import deepcopy
from collections.abc import Mapping

from .contracts import AgentResult, TaskSpec, VerificationResult
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

    def _rejected(self, task: TaskSpec, reason: str = "deterministic_verification_failure") -> AgentResult:
        # Rejection evidence must come from this trusted boundary, not from the
        # verifier that just failed or returned malformed evidence.
        return AgentResult(
            self.agent_id,
            task.task_id,
            "rejected",
            verification=VerificationResult(False, "result", reason),
        )

    def run(self, task: TaskSpec) -> AgentResult:
        try:
            task_check = self.verifier.verify_task(task)
        except Exception:
            return self._rejected(task, "deterministic_task_verification_failure")
        if (
            type(task_check) is not VerificationResult
            or not task_check.is_well_formed()
            or task_check.stage != "contract"
        ):
            return self._rejected(task, "malformed_task_verification")
        if not task_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=task_check)

        try:
            output = task.objective
            if output is None:
                return self._rejected(task, "null_output")
            output_check = self.verifier.verify_output(
                output,
                requirements=task.verification_requirements,
                stage="result",
            )
        except Exception:
            return self._rejected(task, "deterministic_output_verification_failure")
        if (
            type(output_check) is not VerificationResult
            or not output_check.is_well_formed()
            or output_check.stage != "result"
        ):
            return self._rejected(task, "malformed_output_verification")
        if not output_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", output, output_check)
        return AgentResult(self.agent_id, task.task_id, "completed", output, output_check)


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

    def _rejected(self, task: TaskSpec, reason: str = "provider_execution_failure") -> AgentResult:
        # Never promote verifier-supplied rejection evidence after a boundary
        # failure. The rejection record is constructed locally and canonically.
        return AgentResult(
            self.agent_id,
            task.task_id,
            "rejected",
            verification=VerificationResult(False, "result", reason),
        )

    def run(self, task: TaskSpec) -> AgentResult:
        try:
            task_check = self.verifier.verify_task(task)
        except Exception:
            return self._rejected(task, "provider_task_verification_failure")
        if (
            type(task_check) is not VerificationResult
            or not task_check.is_well_formed()
            or task_check.stage != "contract"
        ):
            return self._rejected(task, "malformed_task_verification")
        if not task_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=task_check)

        expected_provider = self.provider
        expected_provider_id = self.provider_id
        expected_model_id = self.model_id
        try:
            current_execute = expected_provider.execute
            if self._callable_fingerprint(current_execute) != self._provider_execute_fingerprint:
                return self._rejected(task)
            expected_execute = current_execute
            response = expected_execute(request_from_task(task))
        except Exception:
            return self._rejected(task)
        if self.provider is not expected_provider or self.provider_id != expected_provider_id or self.model_id != expected_model_id:
            return self._rejected(task, "provider_binding_changed")
        if not isinstance(response, ProviderResponse):
            return self._rejected(task)
        if not isinstance(response.provider_id, str) or not response.provider_id.strip():
            return self._rejected(task, "provider_identity_mismatch")
        if response.provider_id != expected_provider_id:
            return self._rejected(task, "provider_identity_mismatch")
        if not isinstance(response.model_id, str) or not response.model_id.strip() or response.model_id != expected_model_id:
            return self._rejected(task, "provider_identity_mismatch")
        if response.metadata is not None and not isinstance(response.metadata, Mapping):
            return self._rejected(task)
        try:
            isolated_output = deepcopy(response.output)
            if isolated_output is None:
                return self._rejected(task, "null_output")
        except Exception:
            return self._rejected(task)
        try:
            output_check = self.verifier.verify_output(isolated_output, requirements=task.verification_requirements, stage="result")
        except Exception:
            return self._rejected(task, "provider_output_verification_failure")
        if (
            type(output_check) is not VerificationResult
            or not output_check.is_well_formed()
            or output_check.stage != "result"
        ):
            return self._rejected(task, "malformed_output_verification")
        if not output_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", isolated_output, output_check)
        return AgentResult(self.agent_id, task.task_id, "completed", isolated_output, output_check)


__all__ = ["Agent", "DeterministicAgent", "ProviderAgent"]
