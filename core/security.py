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
        if policy is None or verifier is None:
            raise ValueError("policy and verifier are required")
        self.policy = policy
        self.verifier = verifier

    def inspect(self, action: ActionSpec) -> SecurityDecision:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return SecurityDecision(False, "invalid_action", "unknown")
        if action.risk_class not in self.ALLOWED_RISKS:
            return SecurityDecision(False, "risk_requires_explicit_review", action.risk_class)
        try:
            policy_decision = self.policy.evaluate(action)
        except Exception:
            return SecurityDecision(False, "policy_evaluation_failure", action.risk_class)
        if (
            not isinstance(policy_decision, dict)
            or not isinstance(policy_decision.get("allowed"), bool)
            or not policy_decision.get("allowed")
        ):
            reason = policy_decision.get("reason", "policy_denied") if isinstance(policy_decision, dict) else "invalid_policy_decision"
            return SecurityDecision(False, reason, action.risk_class)
        return SecurityDecision(True, "allowed", action.risk_class)

    def allows(self, action: ActionSpec) -> bool:
        return self.inspect(action).allowed

    def verify(self, action: ActionSpec, output):
        decision = self.inspect(action)
        if not decision.allowed:
            return VerificationResult(False, "security", decision.reason)
        try:
            check = self.verifier.verify_output(output, stage="security_result")
        except Exception:
            return VerificationResult(False, "security", "verification_failure")
        if (
            not isinstance(check, VerificationResult)
            or not check.is_well_formed()
            or not check.valid
            or check.stage != "security_result"
        ):
            return VerificationResult(False, "security", "invalid_security_verification")
        return check
