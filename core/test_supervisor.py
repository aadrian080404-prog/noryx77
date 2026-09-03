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
        self.agent_id = "deterministic"

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
        result = AgentResult(self.agent_id, "t1", "completed", "ok", VerificationResult(False, "agent_result", "rejected"))
        check = self.supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "result_verification_failed")

    def test_wrong_task_is_rejected(self):
        result = AgentResult(self.agent_id, "other", "completed", "ok", VerificationResult(True, "agent_result", "ok"))
        check = self.supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "task_id_mismatch")

    def test_selected_agent_identity_is_bound_at_admission(self):
        result = AgentResult("forged-agent", "t1", "completed", "ok", VerificationResult(True, "agent_result", "ok"))
        check = self.supervisor.admit(self.task, result, selected_agent_id=self.agent_id)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_identity_mismatch")

    def test_result_verification_stage_is_bound_at_admission(self):
        result = AgentResult(self.agent_id, "t1", "completed", "ok", VerificationResult(True, "runtime_result", "forged"))
        check = self.supervisor.admit(self.task, result, selected_agent_id=self.agent_id)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "verification_stage_mismatch")

    def test_output_verifier_exception_fails_closed(self):
        class ExplodingVerifier(VerificationEngine):
            def verify_output(self, output, stage=None):
                raise RuntimeError("verification failure")

        supervisor = AgentSupervisor(self.router, ExplodingVerifier())
        result = AgentResult(self.agent_id, "t1", "completed", "ok", VerificationResult(True, "agent_result", "ok"))
        check = supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "verification_failure")

    def test_output_verifier_contract_is_enforced(self):
        class InvalidVerifier(VerificationEngine):
            def verify_output(self, output, stage=None):
                return object()

        supervisor = AgentSupervisor(self.router, InvalidVerifier())
        result = AgentResult(self.agent_id, "t1", "completed", "ok", VerificationResult(True, "agent_result", "ok"))
        check = supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_output_verification")


if __name__ == "__main__":
    unittest.main()
