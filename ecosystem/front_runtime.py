"""Adapters binding the four-front dispatch gateway to concrete runtimes."""
from __future__ import annotations
from typing import Callable, TypeVar
from .boundaries import Front, IntentEnvelope
from .runtime_dispatch import DispatchResult, dispatch
T = TypeVar("T")
def invoke(intent: IntentEnvelope, *, target: Front, execution_id: str, handler: Callable[[], T]) -> DispatchResult:
    return dispatch(intent, source=Front.ORCHESTRATION, target=target, execution_id=execution_id, handler=handler)
def hypersynth(intent: IntentEnvelope, execution_id: str, runtime, task, context) -> DispatchResult:
    return invoke(intent, target=Front.HYPERSYNTH, execution_id=execution_id, handler=lambda: runtime.run(task, interaction_context=context))
def jarvis(intent: IntentEnvelope, execution_id: str, runtime, request, plan) -> DispatchResult:
    return invoke(intent, target=Front.JARVIS, execution_id=execution_id, handler=lambda: runtime.execute(request, plan))
