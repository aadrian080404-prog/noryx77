"""Runtime-bound gateway for cross-front dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from .boundaries import Front, IntentEnvelope
from .dispatch_contract import DispatchReceipt, make_receipt
from .isolation import require_dispatch

T = TypeVar("T")


@dataclass(frozen=True)
class DispatchResult:
    receipt: DispatchReceipt
    value: object | None


def dispatch(
    intent: IntentEnvelope,
    *,
    source: Front,
    target: Front,
    execution_id: str,
    handler: Callable[[], T],
) -> DispatchResult:
    """Dispatch only after validating the cross-front trust topology.

    Authorization and intent/source binding are deliberately checked before
    invoking the handler, so a rejected dispatch can never execute target
    code as a side effect of validation.
    """
    if not isinstance(intent, IntentEnvelope):
        raise TypeError("intent_required")
    if not isinstance(source, Front) or not isinstance(target, Front):
        raise TypeError("invalid_front")
    if source is not intent.front:
        raise PermissionError("intent_source_mismatch")
    require_dispatch(source, target)
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ValueError("invalid_execution_id")
    if not callable(handler):
        raise TypeError("dispatch_handler_required")

    try:
        value = handler()
    except Exception as exc:
        return DispatchResult(
            make_receipt(
                intent,
                source=source,
                target=target,
                execution_id=execution_id,
                accepted=False,
                reason="handler_failure",
                evidence=type(exc).__name__.encode(),
            ),
            None,
        )

    return DispatchResult(
        make_receipt(
            intent,
            source=source,
            target=target,
            execution_id=execution_id,
            accepted=True,
            reason="accepted",
            evidence=repr(type(value)).encode(),
        ),
        value,
    )
