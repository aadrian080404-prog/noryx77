from dataclasses import replace

from .actions import ActionGate
from .contracts import ActionSpec, VerificationResult
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from noryx7_runtime.engine import Intent, PlanStep, RuntimeEngine


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
    _LAZY_EXTERNAL = {
        "contracts": "NORYX7_CONTRACTS",
        "bureaucracy": "NORYX7_BUREAUCRACY",
        "flights": "NORYX7_FLIGHTS",
        "payments": "NORYX7_PAYMENTS",
        "insurance": "NORYX7_INSURANCE",
    }

    def __init__(self, policy_or_gate, verifier, *, runtime_engine=None):
        if type(policy_or_gate) is object:
            raise ValueError("canonical_gate_or_policy_required")
        if isinstance(policy_or_gate, ActionGate):
            self.action_gate = policy_or_gate
        else:
            security = SecurityBoundary(policy_or_gate, verifier)
            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())
        self.verifier = verifier
        if runtime_engine is not None and not isinstance(runtime_engine, RuntimeEngine):
            raise TypeError("invalid_runtime_engine")
        self.runtime_engine = runtime_engine
        self.capabilities = CapabilityRegistry()

    def _runtime_dispatch(self, handler, action, capability_name, execution_id, principal):
        """Route side-effect/high-risk capabilities through the operational execution kernel."""
        risk = self.capabilities.risk(capability_name) or "normal"
        if self._RISK_ORDER.get(risk, 99) < self._RISK_ORDER["high"]:
            return handler(action.target, dict(action.parameters))

        if self.runtime_engine is None:
            raise RuntimeError("runtime_engine_required_for_high_risk_capability")

        principal_id = getattr(principal, "identity", None)
        if principal_id is None:
            principal_id = getattr(principal, "principal_id", None)
        if principal_id is None:
            principal_id = str(principal or "noryx7")

        step = PlanStep(
            step_id=action.action_id,
            action_type=capability_name,
            target=action.target,
            parameters=dict(action.parameters),
        )
        intent = Intent(
            text=f"NORYX7 capability execution: {capability_name}",
            principal_id=str(principal_id),
            intent_id=execution_id or action.execution_id or action.action_id,
        )

        result = self.runtime_engine.execute(
            intent,
            (step,),
            executor=lambda envelope: handler(
                envelope.target,
                dict(envelope.parameters),
            ),
            verifier=lambda envelope, output: bool(
                self.verifier.verify_output(output, stage="runtime_result").valid
            ),
            execution_id=execution_id or action.execution_id or None,
        )

        if getattr(result.status, "value", result.status) != "succeeded":
            raise RuntimeError(result.error or "runtime_execution_failed")

        if len(result.outputs) != 1:
            raise RuntimeError("runtime_execution_output_mismatch")

        return result.outputs[0]

    def _bind_capability_risk(self, action: ActionSpec, capability_name: str) -> ActionSpec:
        configured_risk = self.capabilities.risk(capability_name) or "normal"
        action_risk = action.risk_class or "normal"
        if self._RISK_ORDER.get(configured_risk, 99) > self._RISK_ORDER.get(action_risk, 99):
            action_risk = configured_risk
        requires_authorization = bool(action.requires_authorization or action_risk == "high")
        if action_risk != action.risk_class or requires_authorization != action.requires_authorization:
            return replace(action, risk_class=action_risk, requires_authorization=requires_authorization)
        return action

    def _resolve_lazy_external(self, capability_name):
        if capability_name not in self._LAZY_EXTERNAL or self.capabilities.resolve(capability_name) is not None:
            return
        from .frontier_capabilities import ExternalProviderCapability
        self.capabilities.register(capability_name, ExternalProviderCapability(capability_name, self._LAZY_EXTERNAL[capability_name]), risk_class="high")

    def execute(self, action: ActionSpec, calls_used: int = 0, *, execution_id=None, grant=None, principal=None):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")

        capability_name = action.action_type
        parameters = dict(action.parameters)
        if action.action_type == "jarvis_capability":
            capability_name = parameters.pop("__jarvis_capability", None)

        try:
            self._resolve_lazy_external(capability_name)
        except Exception:
            return None, VerificationResult(False, "tool_policy", "capability_initialization_failure")
        handler = self.capabilities.resolve(capability_name)
        if handler is None:
            return None, VerificationResult(False, "tool_policy", "unknown_capability")

        effective_execution_id = action.execution_id if execution_id is None and action.execution_id else execution_id
        effective_action = self._bind_capability_risk(action, capability_name)

        try:
            decision, output = self.action_gate.authorize_and_execute(
                effective_action,
                lambda: self._runtime_dispatch(
                    handler,
                    effective_action,
                    capability_name,
                    effective_execution_id,
                    principal,
                ),
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
