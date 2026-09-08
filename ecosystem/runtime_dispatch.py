"""Runtime-bound gateway for cross-front dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from .boundaries import Front, IntentEnvelope
from .dispatch_contract import DispatchReceipt, make_receipt
from .isolation import require_dispatch

T = TypeVar("T")
PrincipalAuthorizer = Callable[[str, str], bool]


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
    authorize_principal: PrincipalAuthorizer,
) -> DispatchResult:
    """Dispatch only after explicit principal authorization and trust topology checks."""
    if not isinstance(intent, IntentEnvelope):
        raise TypeError("intent_required")
    if not isinstance(source, Front) or not isinstance(target, Front):
        raise TypeError("invalid_front")
    if source is not intent.front:
        raise PermissionError("intent_source_mismatch")
    if not isinstance(intent.principal_id, str) or not intent.principal_id.strip():
        raise PermissionError("principal_identity_required")
    if not callable(authorize_principal):
        raise TypeError("principal_authorizer_required")
    try:
        authorized = authorize_principal(intent.principal_id, intent.operation)
    except Exception:
        authorized = False
    if authorized is not True:
        raise PermissionError("principal_not_authorized")
    require_dispatch(source, target)
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ValueError("invalid_execution_id")
    if not callable(handler):
        raise TypeError("dispatch_handler_required")

    try:
        value = handler()
    except Exception as exc:
        return DispatchResult(
            make_receipt(intent, source=source, target=target, execution_id=execution_id,
                         accepted=False, reason="handler_failure", evidence=type(exc).__name__.encode()),
            None,
        )

    return DispatchResult(
        make_receipt(intent, source=source, target=target, execution_id=execution_id,
                     accepted=True, reason="accepted", evidence=repr(type(value)).encode()),
        value,
    )
