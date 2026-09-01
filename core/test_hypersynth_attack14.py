import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .reasoning import CrossChecker, Hypothesis


class Attack14Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack14", "research", "objective", "input")

    def result(self, task_id="attack14:s0"):
        return AgentResult("agent", task_id, "completed", "ok", VerificationResult(True, "result", "ok"))

    def test_orphan_hypothesis_basis_cannot_define_execution_mapping(self):
        task = self.task()
        hypotheses = (Hypothesis("h0", task.task_id, "objective", ("foreign:0",)),)
        result = CrossChecker().verify(task, (self.result("foreign:0"),), hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "hypothesis_basis_identity_mismatch")

    def test_multiple_basis_entries_are_rejected(self):
        task = self.task()
        hypotheses = (Hypothesis("h0", task.task_id, "objective", ("attack14:s0", "attack14:s1")),)
        result = CrossChecker().verify(task, (self.result(),), hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_hypothesis_basis")

    def test_valid_prefixed_basis_remains_accepted(self):
        task = self.task()
        hypotheses = (Hypothesis("h0", task.task_id, "objective", ("attack14:s0",)),)
        result = CrossChecker().verify(task, (self.result(),), hypotheses)
        self.assertTrue(result.valid)


if __name__ == "__main__":
    unittest.main()
