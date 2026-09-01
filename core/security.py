from dataclasses import dataclass
from .contracts import ActionSpec, VerificationResult


@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str
    risk_class: str


class SecurityBoundary:
    """Defensive authorization boundary for autonomous actions; deny by default."""
    ALLOWED_RISKS = {"normal", "sensitive"}

    def __init__(self, policy, verifier):
        self.policy = policy
        self.verifier = verifier

    def inspect(self, action: ActionSpec) -> SecurityDecision:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return SecurityDecision(False, "invalid_action", "unknown")
        if action.risk_class not in self.ALLOWED_RISKS:
            return SecurityDecision(False, "risk_requires_explicit_review", action.risk_class)
        policy_decision = self.policy.evaluate(action)
        if not policy_decision.get("allowed", False):
            return SecurityDecision(False, policy_decision.get("reason", "policy_denied"), action.risk_class)
        return SecurityDecision(True, "allowed", action.risk_class)

    def allows(self, action: ActionSpec) -> bool:
        return self.inspect(action).allowed

    def verify(self, action: ActionSpec, output):
        decision = self.inspect(action)
        if not decision.allowed:
            return VerificationResult(False, "security", decision.reason)
        return self.verifier.verify_output(output, stage="security_result")
