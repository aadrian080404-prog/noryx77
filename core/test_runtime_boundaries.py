import unittest

from .actions import ActionGate
from .contracts import ActionSpec, TaskSpec
from .hypersynth_runtime import HypersynthRuntime
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

    def test_hypersynth_objective_limit_is_enforced(self):
        runtime = HypersynthRuntime(limits=RuntimeLimits(max_input_chars=4))
        task = TaskSpec("t3", "compute", "too long", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "objective_limit_exceeded")

    def test_hypersynth_output_limit_is_enforced(self):
        class LargeOutputAgent:
            agent_id = "large"
            def run(self, task):
                from .contracts import AgentResult, VerificationResult
                return AgentResult(self.agent_id, task.task_id, "completed", "x" * 20, VerificationResult(True, "agent_result", "ok"))

        from .router import ResourceRouter
        router = ResourceRouter()
        router.register(LargeOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_chars=5))
        task = TaskSpec("t4", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_limit_exceeded")

    def test_hypersynth_structured_output_item_limit_is_enforced(self):
        class StructuredOutputAgent:
            agent_id = "structured"
            def run(self, task):
                from .contracts import AgentResult, VerificationResult
                output = tuple(range(5))
                return AgentResult(self.agent_id, task.task_id, "completed", output, VerificationResult(True, "agent_result", "ok"))

        from .router import ResourceRouter
        router = ResourceRouter()
        router.register(StructuredOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_items=3))
        task = TaskSpec("t5", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_item_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
