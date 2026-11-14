import unittest

from .contracts import AgentResult, VerificationResult
from .hypersynth import Hypersynth


class HypersynthBoundaryTests(unittest.TestCase):
    def test_consensus_rejects_incomplete_result(self):
        kernel = object.__new__(Hypersynth)
        check = kernel._verify_consensus((AgentResult("a", "t", "running", "x", VerificationResult(True, "result"), "exec-1"),))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "incomplete_result")

    def test_consensus_rejects_duplicate_agent(self):
        kernel = object.__new__(Hypersynth)
        check = kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "x", VerificationResult(True, "result"), "exec-1"),
            AgentResult("a", "t2", "completed", "x", VerificationResult(True, "result"), "exec-1"),
        ))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "duplicate_agent_result")

    def test_consensus_rejects_missing_verification(self):
        kernel = object.__new__(Hypersynth)
        check = kernel._verify_consensus((AgentResult("a", "t", "completed", "x", None, "exec-1"),))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "unverified_result")


if __name__ == "__main__":
    unittest.main()
