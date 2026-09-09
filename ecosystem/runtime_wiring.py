"""Explicit composition root for the four NORYX fronts.

The wiring layer owns composition only: it does not implement business logic,
security policy, or browser/AI behavior. It validates that every front is
registered exactly once and that dispatch enters through the orchestration
front before reaching another front.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, TypeVar

from .boundaries import Front, IntentEnvelope
from .runtime_dispatch import DispatchResult, dispatch

T = TypeVar("T")


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

    def invoke(self, intent: IntentEnvelope, *, execution_id: str) -> DispatchResult:
        if not isinstance(intent, IntentEnvelope):
            raise TypeError("intent_required")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid_execution_id")
        target = intent.front
        target_adapter = self._adapters[target]
        if target is Front.ORCHESTRATION:
            return dispatch(
                intent,
                source=Front.ORCHESTRATION,
                target=Front.ORCHESTRATION,
                execution_id=execution_id,
                handler=lambda: target_adapter.invoke(intent.operation, b"", execution_id),
            )
        orchestration = self._adapters[Front.ORCHESTRATION]
        payload = intent.payload_digest.encode("ascii")
        return dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=target,
            execution_id=execution_id,
            handler=lambda: orchestration.invoke(
                f"dispatch:{target.value}:{intent.operation}", payload, execution_id
            ),
        )

    def invoke_target(self, target: Front, operation: str, payload: bytes, *, execution_id: str) -> DispatchResult:
        if target is Front.ORCHESTRATION:
            raise PermissionError("orchestration_must_enter_via_invoke")
        if not isinstance(target, Front):
            raise TypeError("invalid_target_front")
        intent = IntentEnvelope(
            intent_id=f"wiring:{execution_id}:{target.value}",
            front=Front.ORCHESTRATION,
            operation=operation,
            payload_digest=__import__("hashlib").sha256(payload).hexdigest(),
        )
        return dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=target,
            execution_id=execution_id,
            handler=lambda: self._adapters[target].invoke(operation, payload, execution_id),
        )
