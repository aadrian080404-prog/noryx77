import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class SupervisorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.supervisor = AgentSupervisor(self.router, self.verifier)
        self.task = TaskSpec("t1", "research", "objective", "input")

    def test_valid_result_is_admitted(self):
        result = DeterministicAgent(self.verifier).run(self.task)
        check = self.supervisor.admit(self.task, result)
        self.assertTrue(check.valid)

    def test_malformed_result_is_rejected(self):
        result = AgentResult("agent", "t1", "completed", "ok", object())
        check = self.supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "malformed_agent_result")

    def test_unverified_result_is_rejected(self):
        result = AgentResult("agent", "t1", "completed", "ok", VerificationResult(False, "agent", "rejected"))
        check = self.supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "result_verification_failed")

    def test_wrong_task_is_rejected(self):
        result = AgentResult("agent", "other", "completed", "ok", VerificationResult(True, "agent", "ok"))
        check = self.supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "task_id_mismatch")

    def test_underpowered_preferred_agent_is_rejected_before_execution(self):
        agent = DeterministicAgent(self.verifier, agent_id="medium-agent")
        self.router.register(agent)
        selected, decision = self.supervisor.select(self.task, preferred="medium-agent")
        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "resource_underpowered_for_task")

    def test_sufficient_preferred_agent_is_accepted(self):
        agent = DeterministicAgent(self.verifier, agent_id="large-agent", model_class="large")
        self.router.register(agent)
        selected, decision = self.supervisor.select(self.task, preferred="large-agent")
        self.assertIs(selected, agent)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reason, "agent_selected")

    def test_invalid_model_class_is_rejected(self):
        agent = DeterministicAgent(self.verifier, agent_id="bad-agent", model_class="unknown")
        self.router._agents["bad-agent"] = agent
        selected, decision = self.supervisor.select(self.task, preferred="bad-agent")
        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_route_failure")


if __name__ == "__main__":
    unittest.main()
