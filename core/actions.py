from dataclasses import dataclass

from .contracts import ActionSpec, VerificationResult


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
        if not isinstance(action, ActionSpec):
            return ActionDecision(False, "invalid action", VerificationResult(False, "action_gate", "invalid_action"))
        if not isinstance(calls_used, int) or calls_used < 0:
            return ActionDecision(False, "invalid call count", VerificationResult(False, "action_gate", "invalid_call_count"))
        if calls_used >= self.limits.max_actions_per_task:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        if not action.action_id or not action.action_type:
            return ActionDecision(False, "invalid action contract", VerificationResult(False, "action_gate", "invalid_action_contract"))
        if not self.policy.allows(action):
            return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy"))
        if not self.security.allows(action):
            return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))
