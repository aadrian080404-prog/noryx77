import unittest

from .contracts import ActionSpec
from .policy import PolicyEngine


class SpoofedAction(ActionSpec):
    def __getattribute__(self, name):
        if name == "action_type":
            return "observe"
        if name == "requires_authorization":
            return False
        return super().__getattribute__(name)


class PolicyBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.policy = PolicyEngine()

    def test_attack_277_policy_rejects_action_subclass(self):
        action = SpoofedAction("attack-277", "financial", requires_authorization=True)
        decision = self.policy.evaluate(action)
        self.assertIs(type(decision), dict)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "invalid_action")

    def test_attack_278_policy_allows_only_canonical_safe_action(self):
        action = ActionSpec("attack-278", "observe")
        decision = self.policy.evaluate(action)
        self.assertEqual(decision, {"allowed": True, "reason": "policy_ok"})

    def test_attack_279_policy_denies_high_risk_canonical_action(self):
        action = ActionSpec("attack-279", "financial")
        decision = self.policy.evaluate(action)
        self.assertEqual(decision, {"allowed": False, "reason": "authorization_required"})

    def test_attack_280_allows_fails_closed_on_noncanonical_policy_decision(self):
        class SpoofedPolicy(PolicyEngine):
            def evaluate(self, action):
                return {"allowed": 1, "reason": "forged"}

        self.assertFalse(SpoofedPolicy().allows(ActionSpec("attack-280", "observe")))


if __name__ == "__main__":
    unittest.main()
