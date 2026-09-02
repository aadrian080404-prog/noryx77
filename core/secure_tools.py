"""Fail-closed cryptographic tool boundary for NORYX7."""

from __future__ import annotations

from copy import deepcopy

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity
from .security import SecurityBoundary


class SecureCapabilityRegistry:
    """Capability registry that rejects replacement, risk mismatch, and invalid handlers."""

    VALID_RISKS = frozenset({"normal", "sensitive", "high"})

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        self.crypto = crypto
        self._capabilities = {}

    @staticmethod
    def _fingerprint(handler) -> str:
        return f"{type(handler).__module__}.{type(handler).__qualname__}:{id(handler)}"

    def _capability_tag(self, name: str, risk_class: str, handler) -> str:
        return self.crypto.digest(
            "capability",
            {"name": name, "risk": risk_class, "handler_fingerprint": self._fingerprint(handler)},
        )

    def register(self, name: str, handler, *, risk_class: str = "normal") -> None:
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("invalid_capability")
        if not isinstance(risk_class, str) or risk_class not in self.VALID_RISKS:
            raise ValueError("invalid_capability_risk")
        if name in self._capabilities:
            raise ValueError("duplicate_capability")
        self._capabilities[name] = (handler, risk_class, self._capability_tag(name, risk_class, handler))

    def resolve(self, name: str, *, risk_class: str | None = None):
        item = self._capabilities.get(name)
        if item is None:
            return None
        handler, registered_risk, tag = item
        if not self.crypto.verify_digest(
            "capability",
            {"name": name, "risk": registered_risk, "handler_fingerprint": self._fingerprint(handler)},
            tag,
        ):
            raise RuntimeError("capability_integrity_failure")
        if risk_class is not None and risk_class != registered_risk:
            raise RuntimeError("capability_risk_mismatch")
        return handler

    def risk(self, name: str):
        item = self._capabilities.get(name)
        if item is None:
            return None
        self.resolve(name)
        return item[1]

    def names(self):
        for name in tuple(self._capabilities):
            self.resolve(name)
        return tuple(sorted(self._capabilities))


class SecureToolExecutor:
    """Authenticated capability lookup followed by security/policy authorization and output verification."""

    def __init__(self, policy, verifier, crypto: CryptoIntegrity, security=None):
        self.policy = policy
        self.verifier = verifier
        self.crypto = crypto
        self.security = security or SecurityBoundary(policy, verifier)
        self.capabilities = SecureCapabilityRegistry(crypto)
        self._counter = 0

    def _action_digest(self, action: ActionSpec) -> str:
        return self.crypto.digest(
            "tool_action",
            {
                "action_id": action.action_id,
                "action_type": action.action_type,
                "target": action.target,
                "parameters": dict(action.parameters),
                "risk_class": action.risk_class,
                "requires_authorization": action.requires_authorization,
            },
        )

    def execute(self, action: ActionSpec):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")
        try:
            action_digest = self._action_digest(action)
            action_target = action.target
            action_parameters = deepcopy(dict(action.parameters))
            registered_risk = self.capabilities.risk(action.action_type)
            if registered_risk is None:
                return None, VerificationResult(False, "tool_policy", "unknown_capability")
            if registered_risk != action.risk_class:
                return None, VerificationResult(False, "tool_policy", "capability_risk_mismatch")
            handler = self.capabilities.resolve(action.action_type, risk_class=action.risk_class)
            authorization = self.crypto.sign(
                "tool_execution",
                {
                    "action": action.action_id,
                    "type": action.action_type,
                    "target": action.target,
                    "risk": action.risk_class,
                    "action_digest": action_digest,
                },
                self._counter,
            )
            self._counter += 1
            if not self.crypto.verify(authorization):
                return None, VerificationResult(False, "tool_policy", "cryptographic_authorization_failure")
            try:
                security_decision = self.security.inspect(action)
            except Exception:
                return None, VerificationResult(False, "tool_policy", "security_evaluation_failure")
            if (
                not hasattr(security_decision, "allowed")
                or type(security_decision.allowed) is not bool
                or not hasattr(security_decision, "reason")
                or not isinstance(security_decision.reason, str)
                or not security_decision.reason.strip()
                or not hasattr(security_decision, "risk_class")
                or not isinstance(security_decision.risk_class, str)
                or not security_decision.risk_class.strip()
            ):
                return None, VerificationResult(False, "tool_policy", "malformed_security_decision")
            if security_decision.risk_class != action.risk_class:
                return None, VerificationResult(False, "tool_policy", "security_risk_mismatch")
            if not security_decision.allowed:
                return None, VerificationResult(False, "tool_policy", security_decision.reason)
            try:
                if self._action_digest(action) != action_digest:
                    return None, VerificationResult(False, "tool_policy", "action_runtime_integrity_mismatch")
                current_handler = self.capabilities.resolve(action.action_type, risk_class=action.risk_class)
            except Exception:
                return None, VerificationResult(False, "tool_policy", "capability_runtime_integrity_failure")
            if current_handler is not handler:
                return None, VerificationResult(False, "tool_policy", "capability_runtime_identity_mismatch")
            output = current_handler(action_target, action_parameters)
        except Exception as exc:
            return None, VerificationResult(False, "tool_execution", f"execution_failed:{type(exc).__name__}")
        try:
            check = self.verifier.verify_output(output, stage="tool_result")
        except Exception:
            return None, VerificationResult(False, "tool_result", "verification_failure")
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid:
            return None, VerificationResult(False, "tool_result", "invalid_tool_result_verification")
        return output, check
