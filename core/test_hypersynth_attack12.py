import unittest

from .actions import ActionGate
from .contracts import ActionSpec
from .limits import RuntimeLimits


class RaisingPolicy:
    def allows(self, action):
        raise RuntimeError("policy compromised")


class TruthyPolicy:
    def allows(self, action):
        return object()


class AllowPolicy:
    def allows(self, action):
        return True


class RaisingSecurity:
    def allows(self, action):
        raise RuntimeError("security compromised")


class TruthySecurity:
    def allows(self, action):
        return object()


class AllowSecurity:
    def allows(self, action):
        return True


class Attack12Tests(unittest.TestCase):
    def action(self):
        return ActionSpec("attack12:0", "compute", risk_class="normal")

    def gate(self, policy, security):
        return ActionGate(policy, security, RuntimeLimits())

    def test_policy_exception_fails_closed(self):
        decision = self.gate(RaisingPolicy(), AllowSecurity()).authorize(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy_evaluation_failure")

    def test_policy_truthy_non_boolean_cannot_authorize(self):
        decision = self.gate(TruthyPolicy(), AllowSecurity()).authorize(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "malformed_policy_decision")

    def test_security_exception_fails_closed(self):
        decision = self.gate(AllowPolicy(), RaisingSecurity()).authorize(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "security_evaluation_failure")

    def test_security_truthy_non_boolean_cannot_authorize(self):
        decision = self.gate(AllowPolicy(), TruthySecurity()).authorize(self.action())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "malformed_security_decision")

    def test_valid_boolean_authorization_still_succeeds(self):
        decision = self.gate(AllowPolicy(), AllowSecurity()).authorize(self.action())
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.verification.reason, "authorized")


if __name__ == "__main__":
    unittest.main()
