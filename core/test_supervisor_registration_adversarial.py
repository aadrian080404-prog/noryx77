import unittest

from .agents import Agent
from .contracts import TaskSpec
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class RegisteredAgent:
    agent_id = "trusted"
    model_class = "large"
    capabilities = ()
    capacity_exempt = False

    def run(self, _task):
        raise AssertionError("not executed")


class InjectedRouter:
    def __init__(self, selected):
        self.selected = selected

    def route_for_task(self, _task):
        return self.selected

    def route(self, _agent_id):
        return self.selected

    def get(self, _agent_id):
        return None


class SupervisorRegistrationAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.task = TaskSpec("supervisor-boundary", "research", "answer", {})

    def test_selected_agent_must_be_router_registered_identity(self):
        attacker = RegisteredAgent()
        supervisor = AgentSupervisor(InjectedRouter(attacker), self.verifier)
        agent, decision = supervisor.select(self.task)
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_registration_mismatch")

    def test_preferred_agent_must_also_cross_registration_boundary(self):
        attacker = RegisteredAgent()
        supervisor = AgentSupervisor(InjectedRouter(attacker), self.verifier)
        agent, decision = supervisor.select(self.task, preferred="trusted")
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_registration_mismatch")


if __name__ == "__main__":
    unittest.main()
