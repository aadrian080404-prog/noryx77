import unittest

from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class MutableRoutingAgent(Agent):
    def __init__(self, agent_id="agent", model_class="large"):
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


class RouterRegistrationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.router = ResourceRouter()
        self.verifier = VerificationEngine()
        self.agent = MutableRoutingAgent()
        self.router.register(self.agent)
        self.task = TaskSpec("integrity", "research", "objective", "input")

    def test_model_class_mutation_is_fail_closed(self):
        self.agent.model_class = "micro"
        with self.assertRaises(RuntimeError):
            self.router.route_for_task(self.task)

    def test_capacity_exempt_mutation_cannot_bypass_policy(self):
        self.agent.capacity_exempt = True
        with self.assertRaises(RuntimeError):
            self.router.route_for_task(self.task)

    def test_capabilities_mutation_is_fail_closed(self):
        self.agent.capabilities = ("compute", "privileged")
        with self.assertRaises(RuntimeError):
            self.router.route_for_task(self.task)

    def test_supervisor_cannot_use_mutated_registration(self):
        self.agent.capacity_exempt = True
        supervisor = AgentSupervisor(self.router, self.verifier)
        selected, decision = supervisor.select(self.task)
        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_route_failure")


if __name__ == "__main__":
    unittest.main()
