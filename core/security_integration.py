from dataclasses import dataclass
from typing import Mapping

from .defense import DefenseController


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

    This layer does not execute actions. It decides whether the trusted runtime may
    continue toward the existing capability/action gate.
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
        if envelope.source_zone == envelope.target_zone:
            return {"allowed": True, "reason": "same_zone"}
        return self._controller.authorize(
            principal_id=envelope.principal_id,
            component_id=envelope.component_id,
            source_zone=envelope.source_zone,
            target_zone=envelope.target_zone,
            capability=envelope.capability,
            risk=envelope.risk,
            context=envelope.context or {},
        )

    def allows(self, envelope: SecurityEnvelope) -> bool:
        return bool(self.evaluate(envelope).get("allowed"))
