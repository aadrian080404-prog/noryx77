import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .reasoning import CrossChecker, Hypothesis


class CrossCheckerOutputBoundary213To215Tests(unittest.TestCase):
    def setUp(self):
        self.checker = CrossChecker()
        self.task = TaskSpec(
            "cross-output",
            "analysis",
            "answer",
            {},
            {},
            ("string",),
            "normal",
        )
        self.hypotheses = (Hypothesis("h", "cross-output", "step", ("cross-output:s1",)),)

    def result(self, **kwargs):
        values = dict(
            agent_id="agent",
            task_id="cross-output:s1",
            status="completed",
            output="ok",
            verification=VerificationResult(True, "result", "attacker-accepted"),
        )
        values.update(kwargs)
        return AgentResult(**values)

    def test_attack_213_crosschecker_rejects_empty_output_even_with_valid_verification(self):
        result = self.checker.verify(self.task, (self.result(output=""),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "empty_output")

    def test_attack_214_crosschecker_rejects_wrong_output_type_even_with_valid_verification(self):
        result = self.checker.verify(self.task, (self.result(output=123),), self.hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "output_requirement_mismatch")

    def test_attack_215_crosschecker_rejects_unknown_output_requirement(self):
        task = TaskSpec("cross-output-unknown", "analysis", "answer", {}, {}, ("unknown",), "normal")
        hypotheses = (Hypothesis("h", "cross-output-unknown", "step", ("cross-output-unknown:s1",)),)
        result = self.checker.verify(task, (self.result(task_id="cross-output-unknown:s1"),), hypotheses)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unsupported_output_requirement")


if __name__ == "__main__":
    unittest.main()
