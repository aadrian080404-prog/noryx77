from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult

class CapabilityRegistry:
    """Explicit registry of capabilities. Unknown capabilities are denied."""
    def __init__(self):
        self._capabilities = {}

    def register(self, name, handler, *, risk_class="normal"):
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("invalid_capability")
        if name in self._capabilities:
            raise ValueError("capability_already_registered")
        if not isinstance(risk_class, str) or not risk_class.strip():
            raise ValueError("invalid_capability_risk")
        self._capabilities[name] = (handler, risk_class)

    def resolve(self, name):
        item = self._capabilities.get(name)
        return None if item is None else item[0]

    def risk(self, name):
        item = self._capabilities.get(name)
        return None if item is None else item[1]

    def names(self):
        return tuple(sorted(self._capabilities))


class ToolExecutor:
    """Tool boundary: capability lookup -> policy -> execution -> verification."""
    def __init__(self, policy, verifier):
        self.policy = policy
        self.verifier = verifier
        self.capabilities = CapabilityRegistry()

    def execute(self, action: ActionSpec):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")
        handler = self.capabilities.resolve(action.action_type)
        if handler is None:
            return None, VerificationResult(False, "tool_policy", "unknown_capability")
        try:
            policy_allowed = self.policy.allows(action)
        except Exception:
            return None, VerificationResult(False, "tool_policy", "policy_evaluation_failure")
        if not isinstance(policy_allowed, bool) or not policy_allowed:
            return None, VerificationResult(False, "tool_policy", "action_denied")
        try:
            output = handler(action.target, dict(action.parameters))
        except Exception as exc:
            return None, VerificationResult(False, "tool_execution", f"execution_failed:{type(exc).__name__}")
        try:
            check = self.verifier.verify_output(output, stage="tool_result")
        except Exception:
            return None, VerificationResult(False, "tool_verification", "verification_failure")
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid or check.stage != "tool_result":
            return output, VerificationResult(False, "tool_verification", "invalid_tool_verification")
        return output, check
