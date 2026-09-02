import unittest

from .contracts import ActionSpec, VerificationResult
from .security import SecurityBoundary, SecurityDecision


class SpoofedVerificationResult(VerificationResult):
    def __getattribute__(self, name):
        if name == "valid":
            return True
        if name == "stage":
            return "security_result"
        if name == "reason":
            return "verified"
        return super().__getattribute__(name)


class SpoofedDecision(SecurityDecision):
    def __getattribute__(self, name):
        if name == "allowed":
            return True
        if name == "reason":
            return "allowed"
        if name == "risk_class":
            return "normal"
        return super().__getattribute__(name)


class VerificationProvider:
    def __init__(self, result):
        self.result = result

    def verify_output(self, output, *, stage):
        return self.result


class AllowPolicy:
    def evaluate(self, action):
        return {"allowed": True, "reason": "policy_ok"}


class SecurityBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.action = ActionSpec("action-262", "observe", risk_class="normal")

    def test_attack_262_action_subclass_is_rejected_at_security_boundary(self):
        class SpoofedAction(ActionSpec):
            pass

        action = SpoofedAction(self.action.action_id, self.action.action_type)
        boundary = SecurityBoundary(AllowPolicy(), VerificationProvider(VerificationResult(True, "security_result", "ok")))
        decision = boundary.inspect(action)
        self.assertIs(type(decision), SecurityDecision)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "invalid_action")

    def test_attack_263_security_verification_subclass_is_rejected(self):
        boundary = SecurityBoundary(AllowPolicy(), VerificationProvider(SpoofedVerificationResult(True, "security_result", "verified")))
        result = boundary.verify(self.action, "output")
        self.assertIs(type(result), VerificationResult)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_verification")

    def test_attack_264_canonical_security_decision_remains_exact_type(self):
        boundary = SecurityBoundary(AllowPolicy(), VerificationProvider(VerificationResult(True, "security_result", "verified")))
        decision = boundary.inspect(self.action)
        self.assertIs(type(decision), SecurityDecision)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.risk_class, "normal")

    def test_attack_265_security_allows_fails_closed_on_noncanonical_decision(self):
        class SpoofedBoundary(SecurityBoundary):
            def inspect(self, action):
                return SpoofedDecision(False, "denied", "normal")

        boundary = SpoofedBoundary(AllowPolicy(), VerificationProvider(VerificationResult(True, "security_result", "verified")))
        self.assertFalse(boundary.allows(self.action))

    def test_attack_266_security_verify_accepts_only_canonical_verification_result(self):
        boundary = SecurityBoundary(AllowPolicy(), VerificationProvider(VerificationResult(True, "security_result", "verified")))
        result = boundary.verify(self.action, "output")
        self.assertIs(type(result), VerificationResult)
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
