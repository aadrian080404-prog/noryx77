import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .router import ResourceRouter
from .verification import VerificationEngine

class HypersynthTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.kernel = Hypersynth(self.verifier, self.router)

    def task(self, **kwargs):
        values = dict(task_id="t1", task_type="research", objective="analyze", input="data", risk_class="normal")
        values.update(kwargs)
        return TaskSpec(**values)

    def test_full_controlled_cycle(self):
        result = self.kernel.run(self.task())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["phase"], "metacognition")
        self.assertTrue(result["verification"].valid)

    def test_invalid_task_is_rejected(self):
        result = self.kernel.run(self.task(objective=""))
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["verification"].valid)

    def test_runtime_contains_audit(self):
        result = HypersynthRuntime(self.verifier, self.router).run(self.task())
        self.assertIn("audit", result)
        self.assertEqual(result["status"], "completed")

    def test_disagreement_is_fail_closed(self):
        from .coordination import AgentCoordinator
        from .contracts import AgentResult, VerificationResult
        coordinator = AgentCoordinator(self.router, self.verifier)
        results = (
            AgentResult("a", "t", "completed", "one", VerificationResult(True, "result")),
            AgentResult("b", "t", "completed", "two", VerificationResult(True, "result")),
        )
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

if __name__ == "__main__":
    unittest.main()
