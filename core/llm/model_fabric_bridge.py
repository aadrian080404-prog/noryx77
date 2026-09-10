from __future__ import annotations

from typing import Any
from hashlib import sha256

from noryx7_runtime.model_fabric import ModelFabric, ModelRequest
from core.identity import AgentIdentity
from core.system_fabric import CanonicalSystemFabric


class ModelFabricBridge:
    """Secure bridge between an operational agent and the Model Fabric.

    Model generation remains non-authoritative. When a canonical system fabric is
    present, the agent identity must already hold ``model:execute``; the bridge
    never grants that capability itself.
    """

    MODEL_EXECUTE_CAPABILITY = "model:execute"

    def __init__(self, fabric: ModelFabric, *, runtime_id: str = "", execution_id: str = "", system_fabric: CanonicalSystemFabric | None = None, agent_identity: AgentIdentity | None = None) -> None:
        if not isinstance(fabric, ModelFabric):
            raise TypeError("fabric must be a ModelFabric")
        if not isinstance(runtime_id, str):
            raise TypeError("runtime_id must be a string")
        if not isinstance(execution_id, str):
            raise TypeError("execution_id must be a string")
        if system_fabric is not None and not isinstance(system_fabric, CanonicalSystemFabric):
            raise TypeError("invalid_system_fabric")
        if system_fabric is not None and (not isinstance(agent_identity, AgentIdentity) or not agent_identity.is_well_formed()):
            raise PermissionError("model_agent_identity_required")
        if system_fabric is not None and not execution_id.strip():
            raise PermissionError("model_execution_identity_required")
        fabric_runtime_id = fabric.runtime_id
        if fabric_runtime_id is not None and runtime_id != fabric_runtime_id:
            raise PermissionError("model_runtime_identity_mismatch")
        self._fabric = fabric
        self._runtime_id = runtime_id
        self._execution_id = execution_id
        self._system_fabric = system_fabric
        self._agent_identity = agent_identity

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required")
        if self._system_fabric is not None:
            self._system_fabric.authorize_agent(self._agent_identity, self.MODEL_EXECUTE_CAPABILITY)
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
        result = self._fabric.execute(request)
        if not self._fabric.verify_result(request, result):
            raise RuntimeError("model_fabric_result_verification_failed")
        output = getattr(result, "output", None)
        if not isinstance(output, str):
            raise RuntimeError("model_fabric_non_text_output")
        output = output.strip()
        if not output:
            raise RuntimeError("model_fabric_empty_output")
        result_output_digest = sha256(output.encode("utf-8")).hexdigest()
        envelope_digest = self._fabric.result_digest(request, result)
        if not isinstance(envelope_digest, str) or len(envelope_digest) != 64:
            raise RuntimeError("model_fabric_result_digest_invalid")
        if self._system_fabric is not None:
            self._system_fabric.record_execution(
                execution_id=self._execution_id,
                client_id=self._agent_identity.agent_id,
                runtime_id=self._runtime_id,
                phase="model_verified",
                metadata={
                    "request_digest": self._fabric.request_digest(request),
                    "result_digest": result_output_digest,
                    "result_envelope_digest": envelope_digest,
                    "model_runtime_id": self._runtime_id,
                    "agent_id": self._agent_identity.agent_id,
                },
            )
        return output
