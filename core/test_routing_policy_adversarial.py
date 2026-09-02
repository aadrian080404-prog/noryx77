import unittest

from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .router import ResourceRouter
from .routing_policy import TASK_MODEL_HINTS
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class RoutingAgent(Agent):
    def __init__(self, agent_id, model_class):
        self.agent_id = agent_id
        self.model_class = model_class
        self.capabilities = ()

    def run(self, task):
        return AgentResult(
            self.agent_id,
            task.task_id,
            "completed",
            task.objective,
            VerificationResult(True, "result", "ok"),
        )


class RoutingPolicyAdversarialTests(unittest.TestCase):
    def test_policy_mapping_is_immutable(self):
        with self.assertRaises(TypeError):
            TASK_MODEL_HINTS["research"] = "micro"

    def test_tampered_policy_cannot_downgrade_research_routing(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        medium = RoutingAgent("medium-agent", "medium")
        large = RoutingAgent("large-agent", "large")
        router.register(medium)
        router.register(large)
        supervisor = AgentSupervisor(router, verifier)
        task = TaskSpec("research-attack", "research", "objective", "input")

        selected, decision = supervisor.select(task)

        self.assertTrue(decision.accepted)
        self.assertIs(selected, large)

    def test_policy_object_cannot_be_replaced_through_mapping_alias(self):
        original = TASK_MODEL_HINTS
        self.assertEqual(original["research"], "large")
        self.assertEqual(original["reasoning"], "large")
        self.assertEqual(original["frontier"], "frontier")


if __name__ == "__main__":
    unittest.main()
