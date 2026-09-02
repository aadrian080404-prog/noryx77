from dataclasses import dataclass, asdict
from threading import Lock

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str
    verification: VerificationResult


class ActionGate:
    """Final fail-closed gate before an action can reach a tool/controller."""
    def __init__(self, policy, security, limits, crypto=None, lockdown=None):
        self.policy = policy
        self.security = security
        self.limits = limits
        self.crypto = crypto or CryptoIntegrity()
        self.lockdown = lockdown
        self._authorization_counter = 0
        self._authorization_lock = Lock()

    def _incident(self, category: str, severity: int) -> None:
        if self.lockdown is None:
            return
        try:
            self.lockdown.record_incident(category, severity=severity)
        except Exception:
            # A containment telemetry failure must never turn a deny into an allow.
            pass

    def authorize(self, action: ActionSpec, calls_used: int = 0, tool_calls_used: int = 0) -> ActionDecision:
        if self.lockdown is not None:
            try:
                if not self.lockdown.permits():
                    return ActionDecision(False, "global security lockdown active", VerificationResult(False, "action_gate", "global_lockdown"))
            except Exception:
                return ActionDecision(False, "global security lockdown unavailable", VerificationResult(False, "action_gate", "lockdown_integrity_failure"))
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return ActionDecision(False, "invalid action contract", VerificationResult(False, "action_gate", "invalid_action_contract"))
        if isinstance(calls_used, bool) or not isinstance(calls_used, int) or calls_used < 0:
            return ActionDecision(False, "invalid call count", VerificationResult(False, "action_gate", "invalid_call_count"))
        if isinstance(tool_calls_used, bool) or not isinstance(tool_calls_used, int) or tool_calls_used < 0:
            return ActionDecision(False, "invalid tool call count", VerificationResult(False, "action_gate", "invalid_tool_call_count"))
        if not self.limits.validate_count(calls_used, self.limits.max_actions_per_task):
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        if not self.limits.validate_count(tool_calls_used, self.limits.max_tool_calls_per_task):
            return ActionDecision(False, "tool call budget exceeded", VerificationResult(False, "action_gate", "tool_call_budget"))
        if calls_used >= self.limits.max_actions_per_task:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        try:
            with self._authorization_lock:
                counter = self.crypto.next_counter("action_gate")
                envelope = self.crypto.sign("action_gate", asdict(action), counter)
                self._authorization_counter += 1
                if not self.crypto.verify(envelope):
                    self._incident("action_authorization_integrity_failure", 10)
                    return ActionDecision(False, "cryptographic authorization failure", VerificationResult(False, "action_gate", "authorization_integrity_failure"))
        except Exception:
            self._incident("action_authorization_integrity_failure", 10)
            return ActionDecision(False, "cryptographic authorization failure", VerificationResult(False, "action_gate", "authorization_integrity_failure"))
        try:
            policy_allowed = self.policy.allows(action)
        except Exception:
            return ActionDecision(False, "policy evaluation failed", VerificationResult(False, "action_gate", "policy_evaluation_failure"))
        if type(policy_allowed) is not bool:
            self._incident("malformed_policy_decision", 7)
            return ActionDecision(False, "invalid policy decision", VerificationResult(False, "action_gate", "malformed_policy_decision"))
        if not policy_allowed:
            return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy"))
        try:
            security_allowed = self.security.allows(action)
        except Exception:
            self._incident("security_boundary_failure", 7)
            return ActionDecision(False, "security boundary evaluation failed", VerificationResult(False, "action_gate", "security_evaluation_failure"))
        if type(security_allowed) is not bool:
            self._incident("malformed_security_decision", 7)
            return ActionDecision(False, "invalid security decision", VerificationResult(False, "action_gate", "malformed_security_decision"))
        if not security_allowed:
            return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))
