from .actions import ActionGate
from .contracts import ActionSpec, VerificationResult


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
    """Tool boundary: capability lookup -> ActionGate -> execution -> verification.

    ToolExecutor is intentionally not an independent authorization path. Every tool
    invocation must pass through the canonical ActionGate before its handler runs.
    """
    def __init__(self, action_gate, verifier):
        if not isinstance(action_gate, ActionGate):
            raise ValueError("action_gate_required")
        if not hasattr(verifier, "verify_output") or not callable(verifier.verify_output):
            raise ValueError("verifier_required")
        self.action_gate = action_gate
        self.verifier = verifier
        self.capabilities = CapabilityRegistry()

    def execute(self, action: ActionSpec, calls_used: int = 0, *, execution_id=None, grant=None, principal=None):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")
        handler = self.capabilities.resolve(action.action_type)
        if handler is None:
            return None, VerificationResult(False, "tool_policy", "unknown_capability")

        effective_execution_id = action.execution_id if execution_id is None and action.execution_id else execution_id
        try:
            decision, output = self.action_gate.authorize_and_execute(
                action,
                lambda: handler(action.target, dict(action.parameters)),
                calls_used,
                execution_id=effective_execution_id,
                grant=grant,
                principal=principal,
            )
        except Exception:
            return None, VerificationResult(False, "tool_policy", "action_gate_failure")
        if not decision.allowed:
            return None, VerificationResult(False, "tool_policy", decision.verification.reason or "action_denied")

        try:
            check = self.verifier.verify_output(output, stage="tool_result")
        except Exception:
            return None, VerificationResult(False, "tool_verification", "verification_failure")
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid or check.stage != "tool_result":
            return output, VerificationResult(False, "tool_verification", "invalid_tool_verification")
        return output, check
