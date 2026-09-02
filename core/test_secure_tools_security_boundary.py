import unittest
from concurrent.futures import ThreadPoolExecutor

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

    def test_malformed_security_reason_fails_closed(self):
        class MalformedSecurity:
            def inspect(self, action):
                return type("Decision", (), {"allowed": False, "reason": 123, "risk_class": "normal"})()

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

    def test_security_risk_mismatch_fails_closed(self):
        class MaliciousSecurity:
            def inspect(self, action):
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": "sensitive"})()

        calls = []
        executor = SecureToolExecutor(
            self.policy,
            self.verifier,
            self.crypto,
            security=MaliciousSecurity(),
        )
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
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": "normal"})()

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
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": "normal"})()

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
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": "normal"})()

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
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": "normal"})()

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

    def test_handler_cannot_mutate_original_action_parameters(self):
        parameters = {"nested": {"approved": True}}
        executor = SecureToolExecutor(self.policy, self.verifier, self.crypto)

        def malicious_handler(target, params):
            params["nested"]["approved"] = False
            params["injected"] = "attacker"
            return "ok"

        executor.capabilities.register("compute", malicious_handler)
        action = ActionSpec("isolation", "compute", parameters=parameters)

        output, check = executor.execute(action)

        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)
        self.assertEqual(parameters, {"nested": {"approved": True}})
        self.assertEqual(action.parameters, {"nested": {"approved": True}})

    def test_crypto_authorization_envelope_is_single_use(self):
        crypto = CryptoIntegrity()
        envelope = crypto.sign("tool_execution", {"action": "a", "type": "compute"}, 0)

        self.assertTrue(crypto.verify(envelope))
        self.assertFalse(crypto.verify(envelope))

    def test_crypto_authorization_counter_replay_is_rejected(self):
        crypto = CryptoIntegrity()
        first = crypto.sign("tool_execution", {"action": "a"}, 10)
        second = crypto.sign("tool_execution", {"action": "b"}, 9)

        self.assertTrue(crypto.verify(first))
        self.assertFalse(crypto.verify(second))


if __name__ == "__main__":
    unittest.main()
