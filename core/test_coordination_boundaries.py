import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .coordination import AgentCoordinator
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine


class CoordinationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.coordinator = AgentCoordinator(self.router, self.verifier)
        self.task = TaskSpec("t", "research", "analyze", "data")
        self.plan = Plan("t", (PlanStep("s1", "analyze", "compute", "normal"),))

    def test_execute_accepts_agent_result_with_bound_verification_stage(self):
        results = self.coordinator.execute(self.task, self.plan)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].verification.stage, "agent_result")


if __name__ == "__main__":
    unittest.main()
