import unittest

from .contracts import ActionSpec, VerificationResult
from .crypto import CryptoIntegrity
from .secure_tools import SecureCapabilityRegistry, SecureToolExecutor


class AllowAll:
    def allows(self, action):
        return True


class OutputVerifier:
    def verify_output(self, output, stage):
        return VerificationResult(True, stage, "ok")


class Attack46To50Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)

    def test_attack46_duplicate_capability_is_rejected(self):
        registry = SecureCapabilityRegistry(self.crypto)
        registry.register("compute", lambda target, params: target)
        with self.assertRaisesRegex(ValueError, "duplicate_capability"):
            registry.register("compute", lambda target, params: "forged")

    def test_attack47_capability_risk_downgrade_is_rejected(self):
        registry = SecureCapabilityRegistry(self.crypto)
        registry.register("delete", lambda target, params: target, risk_class="high")
        with self.assertRaisesRegex(RuntimeError, "capability_risk_mismatch"):
            registry.resolve("delete", risk_class="normal")

    def test_attack48_capability_tampering_is_rejected(self):
        registry = SecureCapabilityRegistry(self.crypto)
        registry.register("compute", lambda target, params: target)
        handler, risk, _ = registry._capabilities["compute"]
        registry._capabilities["compute"] = (handler, "high", registry._capabilities["compute"][2])
        with self.assertRaisesRegex(RuntimeError, "capability_integrity_failure"):
            registry.resolve("compute")

    def test_attack49_policy_exception_fails_closed(self):
        class ExplodingPolicy:
            def allows(self, action):
                raise RuntimeError("boom")
        executor = SecureToolExecutor(ExplodingPolicy(), OutputVerifier(), self.crypto)
        executor.capabilities.register("compute", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a49", "compute", target="x"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "policy_evaluation_failure")

    def test_attack50_malformed_output_verification_fails_closed(self):
        class BadVerifier:
            def verify_output(self, output, stage):
                return object()
        executor = SecureToolExecutor(AllowAll(), BadVerifier(), self.crypto)
        executor.capabilities.register("compute", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a50", "compute", target="x"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_tool_result_verification")


if __name__ == "__main__":
    unittest.main()
