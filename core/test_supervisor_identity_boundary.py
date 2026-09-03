import unittest

from .contracts import TaskSpec
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class ForgingRouter:
    def __init__(self, returned_agent_id):
        self.returned_agent_id = returned_agent_id

    def default_id(self):
        return "requested"

    def route(self, preferred):
        return type("FakeAgent", (), {"agent_id": self.returned_agent_id})()


class SupervisorIdentityBoundaryTests(unittest.TestCase):
    def _task(self):
        return TaskSpec("task-1", "search", "find information")

    def test_select_rejects_router_agent_identity_substitution(self):
        supervisor = AgentSupervisor(ForgingRouter("forged"), VerificationEngine())

        agent, decision = supervisor.select(self._task())

        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.agent_id, "requested")
        self.assertEqual(decision.reason, "agent_identity_mismatch")

    def test_select_rejects_agent_without_identity(self):
        class MissingIdentityRouter(ForgingRouter):
            def route(self, preferred):
                return object()

        supervisor = AgentSupervisor(MissingIdentityRouter(None), VerificationEngine())

        agent, decision = supervisor.select(self._task())

        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
