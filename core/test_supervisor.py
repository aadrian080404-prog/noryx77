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

    def test_selected_agent_identity_is_bound_at_admission(self):
        result = AgentResult("forged-agent", "t1", "completed", "ok", VerificationResult(True, "agent_result", "ok"))
        check = self.supervisor.admit(self.task, result, selected_agent_id="real-agent")
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_identity_mismatch")

    def test_result_verification_stage_is_bound_at_admission(self):
        result = AgentResult("real-agent", "t1", "completed", "ok", VerificationResult(True, "runtime_result", "forged"))
        check = self.supervisor.admit(self.task, result, selected_agent_id="real-agent")
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "verification_stage_mismatch")


if __name__ == "__main__":
    unittest.main()
