import unittest

from .actions import ActionGate
from .contracts import ActionSpec, TaskSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine


class AdversarialBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.gate = ActionGate(self.policy, self.security, RuntimeLimits(max_actions_per_task=2))

    def test_action_gate_is_fail_closed_for_none(self):
        self.assertFalse(self.gate.authorize(None).allowed)

    def test_action_gate_rejects_bool_budget(self):
        self.assertFalse(self.gate.authorize(ActionSpec("a", "compute"), True).allowed)

    def test_action_gate_rejects_over_budget(self):
        self.assertFalse(self.gate.authorize(ActionSpec("a", "compute"), 2).allowed)

    def test_security_rejects_high_risk(self):
        action = ActionSpec("a", "compute", risk_class="high")
        self.assertFalse(self.security.allows(action))

    def test_policy_rejects_external_execution(self):
        action = ActionSpec("a", "execute_external")
        self.assertFalse(self.policy.allows(action))

    def test_task_verifier_rejects_non_task(self):
        result = self.verifier.verify_task(object())
        self.assertFalse(result.valid)

    def test_task_verifier_rejects_unknown_risk(self):
        task = TaskSpec("t", "research", "objective", "input", risk_class="unknown")
        self.assertFalse(self.verifier.verify_task(task).valid)

    def test_output_verifier_rejects_none(self):
        self.assertFalse(self.verifier.verify_output(None).valid)


if __name__ == "__main__":
    unittest.main()
