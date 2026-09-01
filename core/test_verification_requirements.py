import unittest

from .contracts import TaskSpec
from .runtime import NORYXRuntime
from .verification import VerificationEngine


class VerificationRequirementTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()

    def test_string_requirement_is_enforced(self):
        check = self.verifier.verify_output(123, requirements=("string",))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "output_type_mismatch")

    def test_unknown_requirement_is_rejected_fail_closed(self):
        task = TaskSpec("req", "research", "analyze", "data", verification_requirements=("invented",))
        check = self.verifier.verify_task(task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "unsupported_verification_requirement")

    def test_runtime_enforces_task_output_requirement(self):
        task = TaskSpec("req-runtime", "research", "analyze", "data", verification_requirements=("string",))
        result = NORYXRuntime().run(task)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["results"][0].verification.valid)

    def test_non_string_agent_output_is_rejected_by_runtime_requirement(self):
        from .agents import Agent
        from .contracts import AgentResult, VerificationResult
        from .policy import PolicyEngine
        from .router import ResourceRouter
        from .security import SecurityBoundary
        from .actions import ActionGate
        from .limits import RuntimeLimits

        class NumericAgent(Agent):
            agent_id = "numeric"

            def run(self, task):
                return AgentResult(self.agent_id, task.task_id, "completed", 123, VerificationResult(True, "result"))

        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(NumericAgent())
        policy = PolicyEngine()
        security = SecurityBoundary(policy, verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        runtime = NORYXRuntime()
        runtime.router = router
        runtime.action_gate = gate
        task = TaskSpec("numeric", "research", "analyze", "data", verification_requirements=("string",))
        result = runtime.run(task, agent_id="numeric")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_type_mismatch")


if __name__ == "__main__":
    unittest.main()
