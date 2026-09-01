from dataclasses import dataclass
from .contracts import ActionSpec, VerificationResult
from .errors import PolicyDenied

@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str
    verification: VerificationResult

class ActionGate:
    """Final gate before an action can reach a tool/controller."""
    def __init__(self, policy, security, limits):
        self.policy = policy
        self.security = security
        self.limits = limits

    def authorize(self, action: ActionSpec, calls_used: int = 0) -> ActionDecision:
        if calls_used >= self.limits.max_actions_per_task:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        if not self.policy.allows(action):
            return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy"))
        if not self.security.allows(action):
            return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))
