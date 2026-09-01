import unittest

from .agents import DeterministicAgent
from .contracts import ActionSpec, AgentResult, TaskSpec
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .supervisor import AgentSupervisor
from .tools import ToolExecutor
from .verification import VerificationEngine

class FoundationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()

    def test_unknown_tool_is_fail_closed(self):
        executor = ToolExecutor(self.policy, self.verifier)
        output, check = executor.execute(ActionSpec("a1", "UNKNOWN"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)

    def test_allowed_tool_output_is_verified(self):
        executor = ToolExecutor(self.policy, self.verifier)
        executor.capabilities.register("search", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a2", "search", target="ok"))
        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)

    def test_security_blocks_high_risk_by_default(self):
        boundary = SecurityBoundary(self.policy, self.verifier)
        check = boundary.inspect(ActionSpec("a3", "publish", risk_class="high"))
        self.assertFalse(check.allowed)

    def test_supervisor_rejects_wrong_task_result(self):
        router = ResourceRouter()
        router.register(DeterministicAgent(self.verifier))
        task = TaskSpec("t1", "demo", "do", "input")
        result = AgentResult("deterministic", "other", "completed", output="ok")
        supervisor = AgentSupervisor(router, self.verifier)
        check = supervisor.admit(task, result)
        self.assertFalse(check.valid)

if __name__ == "__main__":
    unittest.main()
