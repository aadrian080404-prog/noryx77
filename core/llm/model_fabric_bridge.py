from __future__ import annotations

from typing import Any

from core.identity import AgentIdentity
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.model_fabric import ModelFabric, ModelRequest


class ModelFabricBridge:
    """
    Ponte tra LLMBackedAgent e ModelFabric.

    Il bridge concede al modello esclusivamente capacità generativa.
    Quando il runtime espone identità e fabric canonico, la dispatch del modello
    è inoltre vincolata a una capability esplicita e produce provenance digest-only.
    """

    MODEL_EXECUTE_CAPABILITY = "model:execute"

    def __init__(
        self,
        fabric: ModelFabric,
        *,
        runtime_id: str = "",
        execution_id: str = "",
        system_fabric: CanonicalSystemFabric | None = None,
        agent_identity: AgentIdentity | None = None,
    ) -> None:
        if not isinstance(fabric, ModelFabric):
            raise TypeError("fabric must be a ModelFabric")
        if not isinstance(runtime_id, str):
            raise TypeError("runtime_id must be a string")
        if not isinstance(execution_id, str):
            raise TypeError("execution_id must be a string")
        if system_fabric is not None and not isinstance(system_fabric, CanonicalSystemFabric):
            raise TypeError("invalid_system_fabric")
        if agent_identity is not None and not isinstance(agent_identity, AgentIdentity):
            raise TypeError("invalid_agent_identity")
        if system_fabric is not None and agent_identity is None:
            raise ValueError("agent_identity_required_for_system_fabric")

        self._fabric = fabric
        self._runtime_id = runtime_id
        self._execution_id = execution_id
        self._system_fabric = system_fabric
        self._agent_identity = agent_identity

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required")

        request = ModelRequest(
            prompt=prompt,
            required_capabilities=frozenset({"text"}),
            preferred_capabilities=frozenset({"reasoning", "chat"}),
            min_models=1,
            max_models=1,
            tools=(),
            runtime_id=self._runtime_id,
            execution_id=self._execution_id,
        )

        if self._system_fabric is not None:
            identity = self._agent_identity
            assert identity is not None
            self._system_fabric.bind_agent_identity(
                identity,
                capabilities=("execute", self.MODEL_EXECUTE_CAPABILITY),
            )
            self._system_fabric.authorize_agent(identity, self.MODEL_EXECUTE_CAPABILITY)

        result = self._fabric.execute(request)

        output = getattr(result, "output", None)

        if not isinstance(output, str):
            raise RuntimeError("model_fabric_non_text_output")

        output = output.strip()
        if not output:
            raise RuntimeError("model_fabric_empty_output")

        if self._system_fabric is not None:
            self._system_fabric.record_execution(
                execution_id=self._execution_id,
                client_id=self._agent_identity.agent_id,  # type: ignore[union-attr]
                phase="model_completed",
                metadata={
                    "request_digest": self._fabric.request_digest(request),
                    "result_digest": self._fabric.result_digest(request, result),
                    "selected_model": result.selected_model,
                    "runtime_id": result.runtime_id,
                    "agent_id": self._agent_identity.agent_id,  # type: ignore[union-attr]
                },
            )

        return output
