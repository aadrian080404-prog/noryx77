"""Fail-closed cryptographic tool boundary for NORYX7."""

from __future__ import annotations

from copy import deepcopy

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity


class SecureCapabilityRegistry:
    """Capability registry that rejects replacement, risk mismatch, and invalid handlers."""

    VALID_RISKS = frozenset({"normal", "sensitive", "high"})

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        self.crypto = crypto
        self._capabilities = {}

    def register(self, name: str, handler, *, risk_class: str = "normal") -> None:
        if not isinstance(name, str) or not name.strip() or not callable(handler):
            raise ValueError("invalid_capability")
        if not isinstance(risk_class, str) or risk_class not in self.VALID_RISKS:
            raise ValueError("invalid_capability_risk")
        if name in self._capabilities:
            raise ValueError("duplicate_capability")
        self._capabilities[name] = (handler, risk_class, self.crypto.digest("capability", {"name": name, "risk": risk_class}))

    def resolve(self, name: str, *, risk_class: str | None = None):
        item = self._capabilities.get(name)
        if item is None:
            return None
        handler, registered_risk, tag = item
        if not self.crypto.verify_digest("capability", {"name": name, "risk": registered_risk}, tag):
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
    """Authenticated capability lookup followed by policy and output verification."""

    def __init__(self, policy, verifier, crypto: CryptoIntegrity):
        self.policy = policy
        self.verifier = verifier
        self.capabilities = SecureCapabilityRegistry(crypto)
        self.crypto = crypto
        self._counter = 0

    def execute(self, action: ActionSpec):
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return None, VerificationResult(False, "tool_contract", "invalid_action")
        try:
            registered_risk = self.capabilities.risk(action.action_type)
            if registered_risk is None:
                return None, VerificationResult(False, "tool_policy", "unknown_capability")
            if registered_risk != action.risk_class:
                return None, VerificationResult(False, "tool_policy", "capability_risk_mismatch")
            handler = self.capabilities.resolve(action.action_type, risk_class=action.risk_class)
            authorization = self.crypto.sign(
                "tool_execution",
                {"action": action.action_id, "type": action.action_type, "target": action.target, "risk": action.risk_class},
                self._counter,
            )
            self._counter += 1
            if not self.crypto.verify(authorization):
                return None, VerificationResult(False, "tool_policy", "cryptographic_authorization_failure")
            try:
                allowed = self.policy.allows(action)
            except Exception:
                return None, VerificationResult(False, "tool_policy", "policy_evaluation_failure")
            if type(allowed) is not bool or not allowed:
                return None, VerificationResult(False, "tool_policy", "action_denied")
            output = handler(action.target, deepcopy(dict(action.parameters)))
        except Exception as exc:
            return None, VerificationResult(False, "tool_execution", f"execution_failed:{type(exc).__name__}")
        try:
            check = self.verifier.verify_output(output, stage="tool_result")
        except Exception:
            return None, VerificationResult(False, "tool_result", "verification_failure")
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid:
            return None, VerificationResult(False, "tool_result", "invalid_tool_result_verification")
        return output, check
