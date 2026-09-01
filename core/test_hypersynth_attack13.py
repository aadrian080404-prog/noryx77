import unittest

from .contracts import TaskSpec, VerificationResult
from .supervisor import AgentSupervisor


class FakeAgent:
    agent_id = "agent-13"


class Router:
    def __init__(self):
        self.agent = FakeAgent()

    def default_id(self):
        return self.agent.agent_id

    def route(self, agent_id):
        return self.agent if agent_id == self.agent.agent_id else None


class ValidVerifier:
    def verify_task(self, task):
        return VerificationResult(True, "contract", "ok")


class RaisingVerifier:
    def verify_task(self, task):
        raise RuntimeError("verifier compromised")


class MalformedVerifier:
    def verify_task(self, task):
        return object()


class WrongStageVerifier:
    def verify_task(self, task):
        return VerificationResult(True, "output", "ok")


class Attack13Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack13:0", "compute", "run", "input")

    def test_verifier_exception_cannot_admit_agent(self):
        supervisor = AgentSupervisor(Router(), RaisingVerifier())
        agent, decision = supervisor.select(self.task())
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "verifier_task_failure")

    def test_malformed_verifier_response_cannot_admit_agent(self):
        supervisor = AgentSupervisor(Router(), MalformedVerifier())
        agent, decision = supervisor.select(self.task())
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "malformed_task_verification")

    def test_verifier_wrong_stage_cannot_admit_agent(self):
        supervisor = AgentSupervisor(Router(), WrongStageVerifier())
        agent, decision = supervisor.select(self.task())
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "task_verification_stage_mismatch")

    def test_unknown_preferred_agent_cannot_be_admitted(self):
        supervisor = AgentSupervisor(Router(), ValidVerifier())
        agent, decision = supervisor.select(self.task(), preferred="forged-agent")
        self.assertIsNone(agent)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_unavailable")

    def test_valid_selection_still_succeeds(self):
        supervisor = AgentSupervisor(Router(), ValidVerifier())
        agent, decision = supervisor.select(self.task(), preferred="agent-13")
        self.assertIsNotNone(agent)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.agent_id, "agent-13")


if __name__ == "__main__":
    unittest.main()
