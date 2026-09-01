import unittest

from .contracts import ActionSpec, VerificationResult
from .security import SecurityBoundary


class MalformedPolicy:
    def __init__(self, decision):
        self.decision = decision

    def evaluate(self, action):
        return self.decision


class ValidPolicy:
    def evaluate(self, action):
        return {"allowed": True, "reason": "policy_ok"}


class MalformedVerifier:
    def verify_output(self, output, stage=None):
        return object()


class ValidVerifier:
    def verify_output(self, output, stage=None):
        return VerificationResult(True, "security_result", "ok")


class Attack16Tests(unittest.TestCase):
    def action(self):
        return ActionSpec("attack16:0", "compute", risk_class="normal")

    def test_non_boolean_policy_allow_cannot_authorize(self):
        boundary = SecurityBoundary(MalformedPolicy({"allowed": 1, "reason": "forged"}), ValidVerifier())
        decision = boundary.inspect(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "malformed_policy_decision")

    def test_non_text_policy_reason_cannot_authorize(self):
        boundary = SecurityBoundary(MalformedPolicy({"allowed": True, "reason": object()}), ValidVerifier())
        decision = boundary.inspect(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "malformed_policy_decision")

    def test_malformed_output_verification_fails_closed(self):
        boundary = SecurityBoundary(ValidPolicy(), MalformedVerifier())
        result = boundary.verify(self.action(), "output")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_verification")

    def test_valid_security_verification_still_succeeds(self):
        boundary = SecurityBoundary(ValidPolicy(), ValidVerifier())
        result = boundary.verify(self.action(), "output")
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "ok")


if __name__ == "__main__":
    unittest.main()
