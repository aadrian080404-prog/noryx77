import unittest

from .agents import DeterministicAgent, ProviderAgent
from .contracts import TaskSpec, VerificationResult
from .provider import ProviderResponse
from .verification import VerificationEngine


class _Provider:
    provider_id = "trusted"
    model_id = "model-a"

    def execute(self, _request):
        return ProviderResponse("ok", provider_id=self.provider_id, model_id=self.model_id, metadata={})


class _FailingProvider(_Provider):
    def execute(self, _request):
        raise RuntimeError("provider unavailable")


class _WrongStageVerifier(VerificationEngine):
    def verify_task(self, _task):
        return VerificationResult(True, "result", "wrong_stage")

    def verify_output(self, _output, *, requirements=(), stage="result"):
        return VerificationResult(True, "contract", "wrong_stage")


class _ValidNullVerifier(VerificationEngine):
    def verify_task(self, _task):
        return VerificationResult(True, "contract", "task_ok")

    def verify_output(self, _output, *, requirements=(), stage="result"):
        return VerificationResult(True, "result", "accepted_null")


class _RaisesVerifier(VerificationEngine):
    def __init__(self, *, task=False, output=False):
        self.task = task
        self.output = output

    def verify_task(self, task):
        if self.task:
            raise RuntimeError("task verifier down")
        return super().verify_task(task)

    def verify_output(self, output, *, requirements=(), stage="result"):
        if self.output:
            raise RuntimeError("output verifier down")
        return super().verify_output(output, requirements=requirements, stage=stage)


class VerifierStageAndDeterministic206To210Tests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec(
            "verifier-stage-boundary",
            "analysis",
            "answer",
            {},
            {},
            ("string",),
            "normal",
        )

    def test_attack_206_provider_rejects_valid_task_verification_with_wrong_stage(self):
        result = ProviderAgent("agent", _Provider(), _WrongStageVerifier()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_207_provider_cannot_complete_from_valid_output_verification_with_wrong_stage(self):
        class TaskVerifier(VerificationEngine):
            def verify_output(self, _output, *, requirements=(), stage="result"):
                return VerificationResult(True, "contract", "wrong_stage")

        result = ProviderAgent("agent", _Provider(), TaskVerifier()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_208_rejection_path_does_not_trust_valid_verification_of_null_output(self):
        result = ProviderAgent("agent", _FailingProvider(), _ValidNullVerifier()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_209_deterministic_agent_verifier_exception_fails_closed(self):
        result = DeterministicAgent(_RaisesVerifier(task=True)).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_210_deterministic_agent_output_verifier_exception_fails_closed(self):
        result = DeterministicAgent(_RaisesVerifier(output=True)).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)


if __name__ == "__main__":
    unittest.main()
