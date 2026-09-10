from __future__ import annotations

import os
from typing import Any, Iterable, Sequence

from core.identity import AgentIdentity
from core.operational_runtime import OperationalNORYXRuntime
from core.llm.gemini_interactions_bridge import GeminiInteractionsBridge
from noryx7_runtime.model_adapters.gemini_interactions import GeminiInteractionsAdapter, GeminiPart


class GatewayGeminiService:
    """Expose Gemini Interactions only through the canonical NORYX7 runtime boundary."""

    def __init__(self, runtime: OperationalNORYXRuntime) -> None:
        if not isinstance(runtime, OperationalNORYXRuntime):
            raise TypeError("operational_runtime_required")
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        self.runtime = runtime
        self.adapter = GeminiInteractionsAdapter(
            model=os.environ.get("NORYX7_GEMINI_MODEL", "gemini-3.8-flash"),
            api_key=key,
            timeout_seconds=120.0,
        )

    def _bridge(self, execution_id: str) -> GeminiInteractionsBridge:
        agent = self.runtime.router.get("noryx7-llm")
        identity = getattr(agent, "identity", None)
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise PermissionError("operational_agent_identity_invalid")
        return GeminiInteractionsBridge(
            self.adapter,
            runtime_id=self.runtime.model_fabric.runtime_id,
            execution_id=execution_id,
            system_fabric=self.runtime.system_fabric,
            agent_identity=identity,
        )

    @staticmethod
    def parts(payload: Sequence[dict[str, Any]]) -> tuple[GeminiPart, ...]:
        if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
            raise ValueError("gemini_parts_required")
        result = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("invalid_gemini_part")
            result.append(GeminiPart(type=item.get("type", ""), data=item.get("data", ""), mime_type=item.get("mime_type", "")))
        return tuple(result)

    def interact(self, *, execution_id: str, parts: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> dict[str, Any]:
        bridge = self._bridge(execution_id)
        result = bridge.interact(self.parts(parts), tools=tools, previous_interaction_id=previous_interaction_id)
        return {"status": "completed", "execution_id": execution_id, "interaction": result}

    def stream(self, *, execution_id: str, parts: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]] = (), previous_interaction_id: str | None = None) -> Iterable[dict[str, Any]]:
        bridge = self._bridge(execution_id)
        return bridge.stream(self.parts(parts), tools=tools, previous_interaction_id=previous_interaction_id)

    def stream_after_verified_results(self, *, execution_id: str, previous_interaction_id: str, function_results: Sequence[dict[str, Any]]) -> Iterable[dict[str, Any]]:
        bridge = self._bridge(execution_id)
        return bridge.stream_after_verified_results(previous_interaction_id, function_results)
