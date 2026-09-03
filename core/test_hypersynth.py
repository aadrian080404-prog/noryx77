import unittest

from .actions import ActionGate
from .agents import DeterministicAgent
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .metacognition import MetacognitionEngine
from .planning import Plan, PlanStep
from .policy import PolicyEngine
from .reasoning import Hypothesis, InternalSimulator, SimulationResult
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine


class HypersynthTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.kernel = Hypersynth(self.verifier, self.router)

    def task(self, **overrides):
        values = {"task_id": "t", "task_type": "research", "objective": "analyze", "input": "data"}
        values.update(overrides)
        return TaskSpec(**values)

    def test_invalid_task_is_rejected_before_planning(self):
        result = self.kernel.run(self.task(objective=""))
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["verification"].valid)
        self.assertEqual(result["phase"], "perception")

    def test_runtime_contains_audit(self):
        result = HypersynthRuntime(self.verifier, self.router).run(self.task())
        self.assertIn("audit", result)
        self.assertEqual(result["status"], "completed")

    def test_disagreement_is_fail_closed(self):
        from .coordination import AgentCoordinator
        coordinator = AgentCoordinator(self.router, self.verifier)
        results = (
            AgentResult("a", "t", "completed", "one", VerificationResult(True, "result", "agent_result")),
            AgentResult("b", "t", "completed", "two", VerificationResult(True, "result", "agent_result")),
        )
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

    def test_hypersynth_consensus_rejects_duplicate_agent_identity(self):
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", VerificationResult(True, "result")),
            AgentResult("a", "t2", "completed", "same", VerificationResult(True, "result")),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

