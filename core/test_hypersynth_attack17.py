import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .coordination import AgentCoordinator
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine


class RaisingAgent(DeterministicAgent):
    agent_id = "raising"

    def run(self, task):
        raise RuntimeError("compromised agent")


class Attack17Tests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.coordinator = AgentCoordinator(self.router, self.verifier)
        self.task = TaskSpec("attack17", "research", "objective", "input")
        self.plan = Plan("attack17", (PlanStep("attack17:0", "objective", "compute", "normal"),))

    def test_assign_uses_registered_agent_ids(self):
        assignments = self.coordinator.assign(self.plan)
        self.assertEqual(assignments[0].agent_id, "deterministic")
        self.assertEqual(assignments[0].step_id, "attack17:0")

    def test_foreign_step_identity_is_rejected(self):
        plan = Plan("attack17", (PlanStep("foreign:0", "objective", "compute", "normal"),))
        with self.assertRaisesRegex(ValueError, "step_task_identity_mismatch"):
            self.coordinator.assign(plan)

    def test_agent_exception_fails_closed(self):
        router = ResourceRouter()
        router.register(RaisingAgent(self.verifier))
        coordinator = AgentCoordinator(router, self.verifier)
        with self.assertRaisesRegex(RuntimeError, "agent_execution_failure:raising"):
            coordinator.execute(self.task, self.plan)

    def test_valid_execution_still_succeeds(self):
        results = self.coordinator.execute(self.task, self.plan)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], AgentResult)
        self.assertEqual(results[0].task_id, "attack17:0")


if __name__ == "__main__":
    unittest.main()
