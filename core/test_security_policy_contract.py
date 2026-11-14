import unittest

from .contracts import ActionSpec
from .security import SecurityBoundary
from .verification import VerificationEngine


class SecurityPolicyContractTests(unittest.TestCase):
    def test_rejects_non_string_policy_reason(self):
        class ForgedPolicy:
            def evaluate(self, action):
                return {"allowed": False, "reason": {"forged": True}}

        boundary = SecurityBoundary(ForgedPolicy(), VerificationEngine())
        decision = boundary.inspect(ActionSpec("security-contract-1", "search"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "invalid_policy_decision")
        self.assertIsInstance(decision.reason, str)

    def test_rejects_empty_policy_reason(self):
        class ForgedPolicy:
            def evaluate(self, action):
                return {"allowed": False, "reason": "   "}

        boundary = SecurityBoundary(ForgedPolicy(), VerificationEngine())
        decision = boundary.inspect(ActionSpec("security-contract-2", "search"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "invalid_policy_decision")


if __name__ == "__main__":
    unittest.main()
