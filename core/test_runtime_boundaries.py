import unittest

from .actions import ActionGate
from .contracts import ActionSpec, TaskSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .runtime import NORYXRuntime
from .security import SecurityBoundary
from .verification import VerificationEngine

class RuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.runtime = NORYXRuntime()

    def test_normal_task_completes(self):
        task = TaskSpec("t1", "compute", "test objective", "input")
        result = self.runtime.run(task)
        self.assertEqual(result["status"], "completed")

    def test_invalid_task_fails_closed(self):
        task = TaskSpec("", "compute", "test objective", "input")
        self.assertEqual(self.runtime.run(task)["status"], "rejected")

    def test_input_limit_is_enforced(self):
        runtime = NORYXRuntime(RuntimeLimits(max_input_chars=3))
        task = TaskSpec("t2", "compute", "test", "abcd")
        self.assertEqual(runtime.run(task)["status"], "rejected")

    def test_high_risk_action_is_denied(self):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, VerificationEngine())
        gate = ActionGate(policy, security, RuntimeLimits())
        action = ActionSpec("a1", "publish", risk_class="high")
        self.assertFalse(gate.authorize(action).allowed)

if __name__ == "__main__":
    unittest.main()
