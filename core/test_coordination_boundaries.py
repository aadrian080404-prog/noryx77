import unittest

from .agents import Agent, DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
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

    def test_execute_rejects_forged_agent_identity(self):
        class ForgingAgent(Agent):
            agent_id = "real"
            def run(self, task):
                return AgentResult("forged", task.task_id, "completed", "ok", VerificationResult(True, "agent_result"))

        router = ResourceRouter()
        router.register(ForgingAgent())
        coordinator = AgentCoordinator(router, self.verifier)
        with self.assertRaisesRegex(RuntimeError, "agent_result_identity_mismatch:real"):
            coordinator.execute(self.task, self.plan)

    def test_execute_rejects_wrong_verification_stage(self):
        class WrongStageAgent(Agent):
            agent_id = "wrong-stage"
            def run(self, task):
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "runtime_result"))

        router = ResourceRouter()
        router.register(WrongStageAgent())
        coordinator = AgentCoordinator(router, self.verifier)
        with self.assertRaisesRegex(RuntimeError, "agent_result_verification_stage_mismatch:wrong-stage"):
            coordinator.execute(self.task, self.plan)

    def test_consensus_rejects_wrong_verification_stage(self):
        result = AgentResult("agent", "s1", "completed", "ok", VerificationResult(True, "runtime_result", "forged"))
        check = self.coordinator.verify_consensus((result,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "verification_stage_mismatch")


if __name__ == "__main__":
    unittest.main()
