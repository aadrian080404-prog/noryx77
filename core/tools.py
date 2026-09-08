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

    def __init__(self, policy_or_gate, verifier):
        if type(policy_or_gate) is object:
            raise ValueError("canonical_gate_or_policy_required")
        if isinstance(policy_or_gate, ActionGate):
            self.action_gate = policy_or_gate
        else:
            security = SecurityBoundary(policy_or_gate, verifier)
            self.action_gate = ActionGate(
                policy_or_gate,
                security,
                RuntimeLimits(),
            )

        if not hasattr(verifier, "verify_output") or not callable(verifier.verify_output):
            raise ValueError("verifier_required")

        self.verifier = verifier
        self.capabilities = CapabilityRegistry()

    def execute(
        self,
        action: ActionSpec,
        calls_used: int = 0,
        *,
        execution_id=None,
        grant=None,
        principal=None,
    ):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")

        # Canonical delegated JARVIS actions use a distinct Core action
        # type while retaining the original JARVIS capability name in the
        # action parameters. Resolve only this explicit delegation form
        # through the shared capability registry.
        capability_name = action.action_type
        parameters = dict(action.parameters)

        if action.action_type == "jarvis_capability":
            capability_name = parameters.pop("__jarvis_capability", None)

        handler = self.capabilities.resolve(capability_name)
        if handler is None:
            return None, VerificationResult(
                False,
                "tool_policy",
                "unknown_capability",
            )

        effective_execution_id = (
            action.execution_id
            if execution_id is None and action.execution_id
            else execution_id
        )

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
            return None, VerificationResult(
                False,
                "tool_policy",
                "action_gate_failure",
            )

        if not decision.allowed:
            return None, VerificationResult(
                False,
                "tool_policy",
                decision.verification.reason or "action_denied",
            )

        try:
            check = self.verifier.verify_output(
                output,
                stage="tool_result",
            )
        except Exception:
            return None, VerificationResult(
                False,
                "tool_verification",
                "verification_failure",
            )

        if (
            not isinstance(check, VerificationResult)
            or not check.is_well_formed()
            or not check.valid
            or check.stage != "tool_result"
        ):
            return output, VerificationResult(
                False,
                "tool_verification",
                "invalid_tool_verification",
            )

        return output, check
