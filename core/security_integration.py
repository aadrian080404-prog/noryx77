from dataclasses import dataclass
from typing import Mapping

from .defense import AccessRequest, DefenseController, TrustDecision


@dataclass(frozen=True)
class SecurityEnvelope:
    """Minimal security context passed to a defense decision boundary."""

    principal_id: str
    component_id: str
    source_zone: str
    target_zone: str
    capability: str
    risk: str = "normal"
    context: Mapping[str, str] | None = None


class DefenseGate:
    """Fail-closed bridge between runtime actions and the defense control plane.

    This layer does not execute actions. It delegates authorization to the
    canonical DefenseController for every request, including same-zone traffic.
    Same-zone traffic still crosses the authorization boundary; it simply does
    not require a cross-zone segmentation rule.
    """

    def __init__(self, controller: DefenseController):
        if not isinstance(controller, DefenseController):
            raise ValueError("defense_controller_required")
        self._controller = controller

    def evaluate(self, envelope: SecurityEnvelope) -> dict:
        if not isinstance(envelope, SecurityEnvelope):
            return {"allowed": False, "reason": "invalid_security_envelope"}
        fields = (
            envelope.principal_id,
            envelope.component_id,
            envelope.source_zone,
            envelope.target_zone,
            envelope.capability,
            envelope.risk,
        )
        if any(not isinstance(value, str) or not value.strip() for value in fields):
            return {"allowed": False, "reason": "invalid_security_envelope"}
        context = envelope.context or {}
        if not isinstance(context, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in context.items()
        ):
            return {"allowed": False, "reason": "invalid_security_context"}
        session_id = context.get("session_id", "")
        request = AccessRequest(
            principal_id=envelope.principal_id,
            component=envelope.component_id,
            capability=envelope.capability,
            target=envelope.target_zone if envelope.source_zone != envelope.target_zone else "",
            session_id=session_id,
        )
        decision = self._controller.authorize(request)
        return {
            "allowed": decision.decision is TrustDecision.ALLOW,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "mode": decision.mode.value,
        }

    def allows(self, envelope: SecurityEnvelope) -> bool:
        return bool(self.evaluate(envelope).get("allowed"))
