import unittest

from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class BoundaryAgent(Agent):
    def __init__(self, agent_id, model_class):
        self.agent_id = agent_id
        self.model_class = model_class
        self.capabilities = ("compute",)
        self.capacity_exempt = False

    def run(self, task):
        return AgentResult(
            self.agent_id,
            task.task_id,
            "completed",
            task.objective,
            VerificationResult(True, "result", "ok"),
        )


class RoutingBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.router = ResourceRouter()
        self.verifier = VerificationEngine()
        self.supervisor = AgentSupervisor(self.router, self.verifier)
        self.medium = BoundaryAgent("a-medium", "medium")
        self.large = BoundaryAgent("z-large", "large")
        self.router.register(self.medium)
        self.router.register(self.large)
        self.research = TaskSpec("research-boundary", "research", "objective", "input")

    def test_registered_identity_mutation_fails_closed(self):
        self.medium.agent_id = "attacker"
        with self.assertRaises(RuntimeError):
            self.router.available()

    def test_preferred_underpowered_agent_cannot_bypass_supervisor(self):
        selected, decision = self.supervisor.select(self.research, preferred="a-medium")
        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "resource_underpowered_for_task")

    def test_preferred_sufficient_agent_is_selected(self):
        selected, decision = self.supervisor.select(self.research, preferred="z-large")
        self.assertIs(selected, self.large)
        self.assertTrue(decision.accepted)

    def test_default_route_is_task_aware_not_lexicographic(self):
        selected, decision = self.supervisor.select(self.research)
        self.assertIs(selected, self.large)
        self.assertTrue(decision.accepted)


if __name__ == "__main__":
    unittest.main()
