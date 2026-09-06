import unittest

from .actions import ActionGate
from .contracts import ActionSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .tools import ToolExecutor
from .verification import VerificationEngine


class ToolExecutorGateTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.gate = ActionGate(self.policy, self.security, RuntimeLimits(max_actions_per_task=1))
        self.executor = ToolExecutor(self.gate, self.verifier)

    def test_constructor_requires_canonical_gate_or_policy(self):
        with self.assertRaises(ValueError):
            ToolExecutor(object(), self.verifier)

    def test_gate_denial_prevents_handler_execution(self):
        calls = []

        def handler(target, params):
            calls.append(target)
            return target

        self.executor.capabilities.register("publish", handler)
        action = ActionSpec("a1", "publish", target="blocked", risk_class="high")
        output, check = self.executor.execute(action)
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(calls, [])

    def test_gate_budget_prevents_handler_execution(self):
        calls = []
        self.executor.capabilities.register("search", lambda target, params: calls.append(target) or target)
        action = ActionSpec("a2", "search", target="blocked")
        output, check = self.executor.execute(action, calls_used=1)
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(calls, [])

    def test_allowed_execution_is_verified_after_gate(self):
        self.executor.capabilities.register("search", lambda target, params: target)
        output, check = self.executor.execute(ActionSpec("a3", "search", target="ok"))
        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)
        self.assertEqual(check.stage, "tool_result")


if __name__ == "__main__":
    unittest.main()
