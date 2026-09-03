import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .reasoning import CrossChecker, Hypothesis


class CrossCheckerTests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec("t", "research", "analyze", "data")
        self.hypotheses = (Hypothesis("h", "t", "step", ("s1",)),)
        self.checker = CrossChecker()

    def result(self, **kwargs):
        values = dict(agent_id="agent", task_id="s1", status="completed", output="ok", verification=VerificationResult(True, "result", "ok"))
        values.update(kwargs)
        return AgentResult(**values)

    def test_accepts_verified_result(self):
        result = self.checker.verify(self.task, (self.result(),), self.hypotheses)
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "cross_check_ok")

    def test_rejects_duplicate_agent_identity(self):
        results = (self.result(agent_id="a"), self.result(agent_id="a", task_id="s2"))
        hypotheses = (self.hypotheses[0], Hypothesis("h2", "t", "step2", ("s2",)))
        result = self.checker.verify(self.task, results, hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

    def test_rejects_unverified_result(self):
        result = self.checker.verify(self.task, (self.result(verification=None),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unverified_result")

    def test_rejects_invalid_verification(self):
        result = self.checker.verify(self.task, (self.result(verification=VerificationResult(False, "result", "failed")),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unverified_result")

    def test_rejects_verification_identity_mismatch(self):
        result = self.checker.verify(self.task, (self.result(verification=VerificationResult(True, "different-agent", "ok")),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "verification_identity_mismatch")

    def test_rejects_null_output(self):
        result = self.checker.verify(self.task, (self.result(output=None),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "null_output")

    def test_rejects_malformed_result(self):
        result = self.checker.verify(self.task, (self.result(agent_id=" "),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_result")

    def test_rejects_result_step_mapping_mismatch(self):
        result = self.checker.verify(self.task, (self.result(task_id="wrong-step"),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "result_task_mismatch")


if __name__ == "__main__":
    unittest.main()
