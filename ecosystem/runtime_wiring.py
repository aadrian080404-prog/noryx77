"""Explicit composition root for the four NORYX fronts.

The wiring layer owns composition only: it does not implement business logic,
security policy, or browser/AI behavior. It validates that every front is
registered exactly once and that dispatch enters through the orchestration
front before reaching another front.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Mapping

from .boundaries import Front, IntentEnvelope
from .runtime_dispatch import DispatchResult, dispatch


@dataclass(frozen=True)
class FrontAdapter:
    front: Front
    invoke: Callable[[str, bytes, str], object]


class RuntimeWiring:
    """Composition root for JARVIS, Browser, HYPERSYNTH and orchestration."""

    REQUIRED_FRONTS = frozenset(Front)

    def __init__(self, adapters: Mapping[Front, FrontAdapter]):
        if not isinstance(adapters, Mapping):
            raise TypeError("front_adapters_mapping_required")
        normalized = dict(adapters)
        if set(normalized) != set(self.REQUIRED_FRONTS):
            raise ValueError("all_four_front_adapters_required")
        for front, adapter in normalized.items():
            if not isinstance(front, Front) or not isinstance(adapter, FrontAdapter):
                raise TypeError("invalid_front_adapter")
            if adapter.front is not front or not callable(adapter.invoke):
                raise ValueError("front_adapter_binding_invalid")
        self._adapters = normalized

    def registered_fronts(self) -> frozenset[Front]:
        return frozenset(self._adapters)

    @staticmethod
    def _intent(operation: str, payload: bytes, *, execution_id: str) -> IntentEnvelope:
        return IntentEnvelope(
            intent_id=f"wiring:{execution_id}",
            front=Front.ORCHESTRATION,
            operation=operation,
            payload_digest=sha256(payload).hexdigest(),
        )

    def invoke_target(self, target: Front, operation: str, payload: bytes, *, execution_id: str) -> DispatchResult:
        if not isinstance(target, Front):
            raise TypeError("invalid_target_front")
        if target is Front.ORCHESTRATION:
            raise PermissionError("orchestration_must_enter_via_invoke")
        if not isinstance(payload, bytes):
            raise TypeError("payload_bytes_required")
        intent = self._intent(operation, payload, execution_id=execution_id)
        return dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=target,
            execution_id=execution_id,
            handler=lambda: self._adapters[target].invoke(operation, payload, execution_id),
        )

    def invoke(self, intent: IntentEnvelope, *, execution_id: str, payload: bytes | None = None) -> DispatchResult:
        """Invoke an intent while preserving the original payload digest.

        A digest-only envelope cannot be reversed into the original payload; for
        non-orchestration targets the caller must provide the original bytes and
        they must match the envelope digest exactly.
        """
        if not isinstance(intent, IntentEnvelope):
            raise TypeError("intent_required")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid_execution_id")
        if intent.front is Front.ORCHESTRATION:
            if payload not in (None, b""):
                raise ValueError("orchestration_payload_must_be_empty")
            return dispatch(
                intent,
                source=Front.ORCHESTRATION,
                target=Front.ORCHESTRATION,
                execution_id=execution_id,
                handler=lambda: self._adapters[Front.ORCHESTRATION].invoke(intent.operation, b"", execution_id),
            )
        if not isinstance(payload, bytes):
            raise ValueError("original_payload_required")
        if sha256(payload).hexdigest() != intent.payload_digest:
            raise PermissionError("intent_payload_digest_mismatch")
        return dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=intent.front,
            execution_id=execution_id,
            handler=lambda: self._adapters[intent.front].invoke(intent.operation, payload, execution_id),
        )
