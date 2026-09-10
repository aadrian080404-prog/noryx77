from dataclasses import replace

from .actions import ActionGate
from .contracts import ActionSpec, VerificationResult
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary


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
    """Tool boundary: capability lookup -> canonical ActionGate -> execution -> verification."""

    _RISK_ORDER = {"normal": 0, "sensitive": 1, "high": 2}

    def __init__(self, policy_or_gate, verifier):
        if type(policy_or_gate) is object:
            raise ValueError("canonical_gate_or_policy_required")
        if isinstance(policy_or_gate, ActionGate):
            self.action_gate = policy_or_gate
        else:
            security = SecurityBoundary(policy_or_gate, verifier)
            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())
        self.verifier = verifier
        self.capabilities = CapabilityRegistry()

    def _bind_capability_risk(self, action: ActionSpec, capability_name: str) -> ActionSpec:
        configured_risk = self.capabilities.risk(capability_name) or "normal"
        action_risk = action.risk_class or "normal"
        if self._RISK_ORDER.get(configured_risk, 99) > self._RISK_ORDER.get(action_risk, 99):
            action_risk = configured_risk
        requires_authorization = bool(action.requires_authorization or action_risk == "high")
        if action_risk != action.risk_class or requires_authorization != action.requires_authorization:
            return replace(action, risk_class=action_risk, requires_authorization=requires_authorization)
        return action

    def execute(self, action: ActionSpec, calls_used: int = 0, *, execution_id=None, grant=None, principal=None):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")

        capability_name = action.action_type
        parameters = dict(action.parameters)
        if action.action_type == "jarvis_capability":
            capability_name = parameters.pop("__jarvis_capability", None)

        handler = self.capabilities.resolve(capability_name)
        if handler is None:
            return None, VerificationResult(False, "tool_policy", "unknown_capability")

        effective_execution_id = action.execution_id if execution_id is None and action.execution_id else execution_id
        effective_action = self._bind_capability_risk(action, capability_name)

        try:
            decision, output = self.action_gate.authorize_and_execute(
                effective_action,
                lambda: handler(effective_action.target, dict(effective_action.parameters)),
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
