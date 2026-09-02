import unittest

from .agents import DeterministicAgent, ProviderAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .provider import ProviderResponse
from .reasoning import CrossChecker, Hypothesis


class SpoofedVerification(VerificationResult):
    def is_well_formed(self):
        return True


class SpoofedAgentResult(AgentResult):
    def is_well_formed(self):
        return True


class MaliciousVerifier:
    def __init__(self, output=False):
        self.output = output

    def verify_task(self, task):
        if self.output:
            return VerificationResult(True, "contract", "task_ok")
        return SpoofedVerification(True, "contract", "spoofed")

    def verify_output(self, output, requirements=(), stage="result"):
        if self.output:
            return SpoofedVerification(True, "result", "spoofed")
        return VerificationResult(False, "result", "rejected")


class StubProvider:
    provider_id = "stub"
    model_id = "model"

    def execute(self, request):
        return ProviderResponse("ok", self.provider_id, self.model_id, {})


class VerifierEvidenceIntegrity216To220Tests(unittest.TestCase):
    def test_attack_216_deterministic_agent_rejects_subclassed_task_evidence(self):
        task = TaskSpec("t216", "analysis", "answer", {}, {}, ("string",), "normal")
        result = DeterministicAgent(MaliciousVerifier()).run(task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_task_verification")

    def test_attack_217_deterministic_agent_rejects_subclassed_output_evidence(self):
        task = TaskSpec("t217", "analysis", "answer", {}, {}, ("string",), "normal")
        result = DeterministicAgent(MaliciousVerifier(output=True)).run(task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_output_verification")

    def test_attack_218_provider_agent_rejects_subclassed_task_evidence(self):
        task = TaskSpec("t218", "analysis", "answer", {}, {}, ("string",), "normal")
        result = ProviderAgent("provider-agent", StubProvider(), MaliciousVerifier()).run(task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_task_verification")

    def test_attack_219_provider_agent_rejects_subclassed_output_evidence(self):
        task = TaskSpec("t219", "analysis", "answer", {}, {}, ("string",), "normal")
        result = ProviderAgent("provider-agent", StubProvider(), MaliciousVerifier(output=True)).run(task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_output_verification")

    def test_attack_220_crosschecker_rejects_subclassed_result_evidence(self):
        checker = CrossChecker()
        task = TaskSpec("t220", "analysis", "answer", {}, {}, ("string",), "normal")
        hypothesis = Hypothesis("h", "t220", "step", ("t220:s1",))
        result = SpoofedAgentResult("agent", "t220:s1", "completed", "ok", VerificationResult(True, "result", "ok"))
        checked = checker.verify(task, (result,), (hypothesis,))
        self.assertFalse(checked.valid)
        self.assertEqual(checked.reason, "invalid_result_type")


if __name__ == "__main__":
    unittest.main()
