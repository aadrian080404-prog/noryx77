import unittest

from .contracts import AgentResult, VerificationResult
from .hypersynth import Hypersynth


class HypersynthAdversarialTests(unittest.TestCase):
    def test_consensus_rejects_incomplete_result(self):
        kernel = object.__new__(Hypersynth)
        result = kernel._verify_consensus((
            AgentResult("a", "t1", "running", "same", VerificationResult(True, "result"), "exec-1"),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "incomplete_result")

    def test_consensus_rejects_duplicate_agent_identity(self):
        kernel = object.__new__(Hypersynth)
        result = kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", VerificationResult(True, "result"), "exec-1"),
            AgentResult("a", "t2", "completed", "same", VerificationResult(True, "result"), "exec-1"),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

    def test_consensus_rejects_unverified_result(self):
        kernel = object.__new__(Hypersynth)
        result = kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", None, "exec-1"),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unverified_result")


if __name__ == "__main__":
    unittest.main()
