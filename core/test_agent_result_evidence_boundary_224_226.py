import unittest

from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth


class SpoofedAgentResult(AgentResult):
    def __getattribute__(self, name):
        if name == "agent_id":
            return "trusted-agent"
        if name == "task_id":
            return "task-224:0"
        if name == "status":
            return "completed"
        if name == "output":
            return "attacker-output"
        return super().__getattribute__(name)

    def is_well_formed(self):
        return True


class SpoofedVerification(VerificationResult):
    def is_well_formed(self):
        return True


class EvidenceAgent(Agent):
    def __init__(self, result):
        self.agent_id = "trusted-agent"
        self.result = result

    def run(self, _task):
        return self.result


class AgentResultEvidenceBoundary224To226Tests(unittest.TestCase):
    def setUp(self):
        self.kernel = Hypersynth.__new__(Hypersynth)
        self.kernel.audit = type("Audit", (), {"record": lambda *args, **kwargs: None})()
        self.kernel.max_agents = 1
        self.kernel.verifier = type("Verifier", (), {
            "verify_output": lambda _self, output, requirements=(), stage="runtime_output": VerificationResult(True, stage, "ok")
        })()

    def child(self):
        return TaskSpec("task-224:0", "analysis", "answer", {}, {}, ("string",), "normal")

    def test_attack_224_subclassed_agent_result_cannot_cross_runtime_boundary(self):
        result = SpoofedAgentResult(
            "attacker-agent", "foreign-task", "completed", "attacker-output",
            VerificationResult(True, "result", "ok"),
        )
        check = self.kernel._verify_agent_result(self.child(), EvidenceAgent(result), result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_agent_result")

    def test_attack_225_canonical_agent_result_cannot_carry_spoofed_verification_subclass(self):
        result = AgentResult(
            "trusted-agent", "task-224:0", "completed", "safe-output",
            SpoofedVerification(True, "result", "spoofed"),
        )
        check = self.kernel._verify_agent_result(self.child(), EvidenceAgent(result), result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "malformed_result_verification")

    def test_attack_226_exact_agent_result_and_verification_are_accepted(self):
        verification = VerificationResult(True, "result", "ok")
        result = AgentResult("trusted-agent", "task-224:0", "completed", "safe-output", verification)
        check = self.kernel._verify_agent_result(self.child(), EvidenceAgent(result), result)
        self.assertTrue(check.valid)
        self.assertEqual(check.reason, "independent_result_verified")


if __name__ == "__main__":
    unittest.main()
