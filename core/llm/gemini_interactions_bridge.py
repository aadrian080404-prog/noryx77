from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence

from core.identity import AgentIdentity
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.model_adapters.gemini_interactions import GeminiInteractionsAdapter, GeminiPart


class GeminiInteractionsBridge:
    """Authorize and audit Gemini Interactions without bypassing NORYX7 policy."""

    MODEL_EXECUTE_CAPABILITY = "model:execute"

    def __init__(self, adapter: GeminiInteractionsAdapter, *, runtime_id: str, execution_id: str, system_fabric: CanonicalSystemFabric, agent_identity: AgentIdentity) -> None:
        if not isinstance(adapter, GeminiInteractionsAdapter):
            raise TypeError("adapter must be a GeminiInteractionsAdapter")
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise ValueError("runtime_id is required")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id is required")
        if not isinstance(system_fabric, CanonicalSystemFabric):
            raise TypeError("system_fabric is required")
        if not isinstance(agent_identity, AgentIdentity) or not agent_identity.is_well_formed():
            raise PermissionError("gemini_agent_identity_required")
        self._adapter = adapter
        self._runtime_id = runtime_id
        self._execution_id = execution_id
        self._system_fabric = system_fabric
        self._agent_identity = agent_identity

    @staticmethod
    def _digest(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

    def _authorize(self) -> None:
        self._system_fabric.authorize_agent(self._agent_identity, self.MODEL_EXECUTE_CAPABILITY)

    def _record(self, phase: str, metadata: dict[str, Any]) -> None:
        self._system_fabric.record_execution(
            execution_id=self._execution_id,
            client_id=self._agent_identity.agent_id,
            runtime_id=self._runtime_id,
            phase=phase,
            metadata={"agent_id": self._agent_identity.agent_id, "provider": self._adapter.name, **metadata},
        )

    def interact(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> dict[str, Any]:
        self._authorize()
        result = self._adapter.interact(parts, tools=tools, previous_interaction_id=previous_interaction_id)
        if not isinstance(result, dict):
            raise RuntimeError("gemini_interactions_result_invalid")
        self._record("gemini_interaction_verified", {
            "request_digest": self._digest([part.as_payload() for part in parts]),
            "result_digest": self._digest(result),
            "previous_interaction_id": previous_interaction_id,
            "interaction_id": result.get("id") or result.get("interaction", {}).get("id"),
            "function_calls_present": bool(self._adapter.extract_function_calls(result)),
        })
        return result

    def continue_after_verified_results(self, previous_interaction_id: str, function_results: Sequence[dict[str, Any]]) -> dict[str, Any]:
        self._authorize()
        result = self._adapter.continue_interaction(previous_interaction_id, function_results)
        if not isinstance(result, dict):
            raise RuntimeError("gemini_interactions_continuation_invalid")
        self._record("gemini_interaction_continued", {
            "previous_interaction_id": previous_interaction_id,
            "function_results_digest": self._digest(function_results),
            "result_digest": self._digest(result),
            "interaction_id": result.get("id") or result.get("interaction", {}).get("id"),
        })
        return result

    def stream(self, parts: Sequence[GeminiPart], *, tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> Iterable[dict[str, Any]]:
        self._authorize()
        request_digest = self._digest([part.as_payload() for part in parts])
        for event in self._adapter.stream(parts, tools=tools, previous_interaction_id=previous_interaction_id):
            if not isinstance(event, dict):
                raise RuntimeError("gemini_interactions_stream_event_invalid")
            self._record("gemini_stream_event", {"request_digest": request_digest, "previous_interaction_id": previous_interaction_id, "event_digest": self._digest(event), "event_type": event.get("event_type", event.get("type", "unknown"))})
            yield event

    def stream_after_verified_results(self, previous_interaction_id: str, function_results: Sequence[dict[str, Any]]) -> Iterable[dict[str, Any]]:
        self._authorize()
        results_digest = self._digest(function_results)
        for event in self._adapter.stream_function_results(previous_interaction_id, function_results):
            if not isinstance(event, dict):
                raise RuntimeError("gemini_interactions_continuation_event_invalid")
            self._record("gemini_continuation_stream_event", {"previous_interaction_id": previous_interaction_id, "function_results_digest": results_digest, "event_digest": self._digest(event), "event_type": event.get("event_type", event.get("type", "unknown"))})
            yield event
