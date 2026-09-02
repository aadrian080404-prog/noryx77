import unittest
from concurrent.futures import ThreadPoolExecutor

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity
from .secure_tools import SecureToolExecutor
from .security import SecurityBoundary, SecurityDecision
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
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto, security=MalformedSecurity())
        executor.capabilities.register("compute", lambda target, params: "must-not-run")
        output, check = executor.execute(ActionSpec("a", "compute"))
        self.assertIsNone(output)
        self.assertEqual(check, VerificationResult(False, "tool_policy", "malformed_security_decision"))

    def test_malformed_security_reason_fails_closed(self):
        class MalformedSecurity:
            def inspect(self, action):
                return type("Decision", (), {"allowed": False, "reason": 123, "risk_class": "normal"})()
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto, security=MalformedSecurity())
        executor.capabilities.register("compute", lambda target, params: "must-not-run")
        output, check = executor.execute(ActionSpec("a", "compute"))
        self.assertIsNone(output)
        self.assertEqual(check, VerificationResult(False, "tool_policy", "malformed_security_decision"))

    def test_security_risk_mismatch_fails_closed(self):
        class MaliciousSecurity:
            def inspect(self, action):
                return SecurityDecision(True, "allowed", "sensitive")
        calls = []
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto, security=MaliciousSecurity())
        executor.capabilities.register("compute", lambda target, params: calls.append(True) or "must-not-run")
        output, check = executor.execute(ActionSpec("a", "compute", risk_class="normal"))
        self.assertIsNone(output)
        self.assertEqual(check, VerificationResult(False, "tool_policy", "security_risk_mismatch"))
        self.assertEqual(calls, [])

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
                return SecurityDecision(True, "allowed", "normal")
        executor.security = SwappingSecurity()
        output, check = executor.execute(ActionSpec("a", "compute"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "capability_runtime_integrity_failure")
        self.assertEqual(calls, [])

    def test_action_parameter_mutation_during_security_is_rejected(self):
        calls = []
        parameters = {"approved": True}
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: calls.append(params) or "forged")
        class MutatingSecurity:
            def inspect(self, action):
                parameters["approved"] = False
                return SecurityDecision(True, "allowed", "normal")
        executor.security = MutatingSecurity()
        output, check = executor.execute(ActionSpec("a", "compute", parameters=parameters))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "action_runtime_integrity_mismatch")
        self.assertEqual(calls, [])

    def test_nested_action_parameter_mutation_during_security_is_rejected(self):
        calls = []
        parameters = {"nested": {"approved": True}}
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: calls.append(params) or "forged")
        class MutatingSecurity:
            def inspect(self, action):
                parameters["nested"]["approved"] = False
                return SecurityDecision(True, "allowed", "normal")
        executor.security = MutatingSecurity()
        output, check = executor.execute(ActionSpec("a", "compute", parameters=parameters))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "action_runtime_integrity_mismatch")
        self.assertEqual(calls, [])

    def test_action_requires_authorization_mutation_during_security_is_rejected(self):
        calls = []
        action = ActionSpec("a", "compute", requires_authorization=False)
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: calls.append(True) or "forged")
        class MutatingSecurity:
            def inspect(self, inspected):
                object.__setattr__(inspected, "requires_authorization", True)
                return SecurityDecision(True, "allowed", "normal")
        executor.security = MutatingSecurity()
        output, check = executor.execute(action)
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "action_runtime_integrity_mismatch")
        self.assertEqual(calls, [])

    def test_concurrent_execution_preserves_unique_authorization_counter(self):
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor.capabilities.register("compute", lambda target, params: target)
        actions = [ActionSpec(f"action-{index}", "compute", target=str(index)) for index in range(32)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(executor.execute, actions))
        self.assertEqual([output for output, check in results], [str(index) for index in range(32)])
        self.assertTrue(all(check.valid for _, check in results))
        self.assertEqual(executor._counter, 32)

    def test_shared_crypto_across_executors_preserves_monotonic_counters(self):
        executor_a = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor_b = SecureToolExecutor(self.policy, self.verifier, self.crypto)
        executor_a.capabilities.register("compute", lambda target, params: target)
        executor_b.capabilities.register("compute", lambda target, params: target)
        actions = [ActionSpec(f"shared-{index}", "compute", target=str(index)) for index in range(64)]
        def run(indexed):
            index, action = indexed
            return (executor_a if index % 2 == 0 else executor_b).execute(action)
        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(run, enumerate(actions)))
        self.assertTrue(all(check.valid for _, check in results))


if __name__ == "__main__":
    unittest.main()
