from dataclasses import dataclass
from .contracts import ActionSpec, VerificationResult

@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str
    risk_class: str

class SecurityBoundary:
    """Defensive boundary for future tools and autonomous actions."""
    ALLOWED_RISKS = {"normal", "sensitive"}

    def __init__(self, policy, verifier):
        self.policy = policy
        self.verifier = verifier

    def inspect(self, action: ActionSpec) -> SecurityDecision:
        if not isinstance(action, ActionSpec):
            return SecurityDecision(False, "invalid_action", "unknown")
        if action.risk_class not in self.ALLOWED_RISKS:
            return SecurityDecision(False, "risk_requires_explicit_review", action.risk_class)
        if hasattr(self.policy, "allows") and not self.policy.allows(action):
            return SecurityDecision(False, "policy_denied", action.risk_class)
        return SecurityDecision(True, "allowed", action.risk_class)

    def verify(self, action: ActionSpec, output):
        decision = self.inspect(action)
        if not decision.allowed:
            return VerificationResult(False, "security", decision.reason)
        return self.verifier.verify_output(output, stage="security_result")
