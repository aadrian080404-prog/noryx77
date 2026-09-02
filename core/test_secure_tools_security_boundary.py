import unittest

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity
from .secure_tools import SecureToolExecutor
from .security import SecurityBoundary
from .verification import VerificationEngine


class PermissivePolicy:
    def evaluate(self, action):
        return {"allowed": True, "reason": "permissive"}

    def allows(self, action):
        return True


class SecureToolSecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PermissivePolicy()
        self.crypto = CryptoIntegrity()

    def test_executor_enforces_security_even_when_policy_is_permissive(self):
        calls = []
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: calls.append((target, params)) or "ok")

        output, check = executor.execute(ActionSpec("a", "compute", target="safe"))

        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)
        self.assertEqual(calls, [("safe", {})])
        self.assertIsInstance(executor.security, SecurityBoundary)

    def test_high_risk_capability_cannot_bypass_security_boundary(self):
        calls = []
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("danger", lambda target, params: calls.append(True) or "unsafe", risk_class="high")

        output, check = executor.execute(ActionSpec("a", "danger", risk_class="high"))

        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "risk_requires_explicit_review")
        self.assertEqual(calls, [])

    def test_malformed_security_decision_fails_closed(self):
        class MalformedSecurity:
            def inspect(self, action):
                return object()

        executor = SecureToolExecutor(
            self.policy,
            self.verifier,
            self.crypto,
            security=MalformedSecurity(),
        )
        executor.capabilities.register("compute", lambda target, params: "must-not-run")

        output, check = executor.execute(ActionSpec("a", "compute"))

        self.assertIsNone(output)
        self.assertEqual(check, VerificationResult(False, "tool_policy", "malformed_security_decision"))

    def test_security_phase_capability_swap_is_rejected_before_handler_execution(self):
        calls = []
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: calls.append("original") or "original")

        class SwappingSecurity:
            def inspect(self, action):
                executor.capabilities._capabilities["compute"] = (
                    lambda target, params: calls.append("forged") or "forged",
                    "normal",
                    executor.capabilities._capabilities["compute"][2],
                )
                return type("Decision", (), {"allowed": True})()

        executor.security = SwappingSecurity()
        output, check = executor.execute(ActionSpec("a", "compute"))

        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "capability_runtime_integrity_failure")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
