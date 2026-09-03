from dataclasses import dataclass

from .contracts import ActionSpec, VerificationResult


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str
    verification: VerificationResult


class ActionGate:
    """Final fail-closed gate before an action can reach a tool/controller."""
    def __init__(self, policy, security, limits):
        self.policy = policy
        self.security = security
        self.limits = limits

    def authorize(self, action: ActionSpec, calls_used: int = 0, *, execution_id: str | None = None) -> ActionDecision:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return ActionDecision(False, "invalid action contract", VerificationResult(False, "action_gate", "invalid_action_contract"))
        if isinstance(calls_used, bool) or not isinstance(calls_used, int) or calls_used < 0:
            return ActionDecision(False, "invalid call count", VerificationResult(False, "action_gate", "invalid_call_count"))
        if execution_id is not None:
            if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id.encode("utf-8")) > 256:
                return ActionDecision(False, "invalid execution identity", VerificationResult(False, "action_gate", "invalid_execution_identity"))
            if action.execution_id != execution_id:
                return ActionDecision(False, "execution identity mismatch", VerificationResult(False, "action_gate", "execution_identity_mismatch"))
        elif action.execution_id:
            return ActionDecision(False, "execution identity required", VerificationResult(False, "action_gate", "execution_identity_required"))
        remaining = self.limits.max_actions_per_task - calls_used
        if remaining <= 0:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        try:
            policy_allowed = self.policy.allows(action)
        except Exception:
            return ActionDecision(False, "policy evaluation failure", VerificationResult(False, "action_gate", "policy_evaluation_failure"))
        if not policy_allowed:
            return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy"))
        try:
            security_allowed = self.security.allows(action)
        except Exception:
            return ActionDecision(False, "security evaluation failure", VerificationResult(False, "action_gate", "security_evaluation_failure"))
        if not security_allowed:
            return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))
