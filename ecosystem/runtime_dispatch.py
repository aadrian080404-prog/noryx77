"""Runtime-bound gateway for cross-front dispatch."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TypeVar
from .boundaries import Front, IntentEnvelope
from .dispatch_contract import DispatchReceipt, make_receipt
T = TypeVar("T")
@dataclass(frozen=True)
class DispatchResult:
    receipt: DispatchReceipt
    value: object | None
def dispatch(intent: IntentEnvelope, *, source: Front, target: Front, execution_id: str, handler: Callable[[], T]) -> DispatchResult:
    if not callable(handler):
        raise TypeError("dispatch_handler_required")
    try:
        value = handler()
    except Exception as exc:
        return DispatchResult(make_receipt(intent, source=source, target=target, execution_id=execution_id, accepted=False, reason="handler_failure", evidence=type(exc).__name__.encode()), None)
    return DispatchResult(make_receipt(intent, source=source, target=target, execution_id=execution_id, accepted=True, reason="accepted", evidence=repr(type(value)).encode()), value)
