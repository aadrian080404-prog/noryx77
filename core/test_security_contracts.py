import unittest

from .actions import ActionGate
from .contracts import ActionSpec, TaskSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine


class SecurityContractTests(unittest.TestCase):
    def setUp(self):
        verifier = VerificationEngine()
        policy = PolicyEngine()
        security = SecurityBoundary(policy, verifier)
        self.gate = ActionGate(policy, security, RuntimeLimits(max_actions_per_task=2))

    def test_malformed_action_denied(self):
        decision = self.gate.authorize(object())
        self.assertFalse(decision.allowed)

    def test_unknown_action_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "unknown"))
        self.assertFalse(decision.allowed)

    def test_high_risk_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "publish", risk_class="normal"))
        self.assertFalse(decision.allowed)

    def test_high_risk_class_denied_by_security(self):
        decision = self.gate.authorize(ActionSpec("a", "compute", risk_class="high"))
        self.assertFalse(decision.allowed)

    def test_authorization_flag_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "compute", requires_authorization=True))
        self.assertFalse(decision.allowed)

    def test_budget_boundary(self):
        action = ActionSpec("a", "compute")
        self.assertTrue(self.gate.authorize(action, calls_used=1).allowed)
        self.assertFalse(self.gate.authorize(action, calls_used=2).allowed)

    def test_negative_call_count_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "compute"), calls_used=-1)
        self.assertFalse(decision.allowed)


class TaskContractTests(unittest.TestCase):
    def test_invalid_risk_is_rejected(self):
        task = TaskSpec("t", "research", "objective", "input", risk_class="unknown")
        self.assertFalse(VerificationEngine().verify_task(task).valid)

    def test_empty_required_fields_are_rejected(self):
        task = TaskSpec("", "research", "objective", "input")
        self.assertFalse(VerificationEngine().verify_task(task).valid)


if __name__ == "__main__":
    unittest.main()
