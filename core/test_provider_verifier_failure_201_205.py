import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec, VerificationResult
from .provider import ProviderResponse
from .verification import VerificationEngine


class _Provider:
    provider_id = "trusted"
    model_id = "model-a"

    def __init__(self, output="ok"):
        self.output = output

    def execute(self, _request):
        return ProviderResponse(self.output, provider_id=self.provider_id, model_id=self.model_id, metadata={})


class _VerifierRaises(VerificationEngine):
    def verify_task(self, _task):
        raise RuntimeError("verifier down")

    def verify_output(self, _output, *, requirements=(), stage="result"):
        raise RuntimeError("verifier down")


class _VerifierMalformed(VerificationEngine):
    def verify_task(self, _task):
        return object()

    def verify_output(self, _output, *, requirements=(), stage="result"):
        return object()


class ProviderVerifierFailure201To205Tests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec(
            "provider-verifier-boundary",
            "analysis",
            "answer",
            {},
            {},
            ("string",),
            "normal",
        )

    def test_attack_201_verifier_task_exception_fails_closed(self):
        result = ProviderAgent("agent", _Provider(), _VerifierRaises()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_202_malformed_task_verification_fails_closed(self):
        result = ProviderAgent("agent", _Provider(), _VerifierMalformed()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_203_verifier_output_exception_fails_closed(self):
        class TaskVerifier(VerificationEngine):
            def verify_task(self, task):
                return super().verify_task(task)

            def verify_output(self, _output, *, requirements=(), stage="result"):
                raise RuntimeError("verifier output down")

        result = ProviderAgent("agent", _Provider(), TaskVerifier()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_204_malformed_output_verification_fails_closed(self):
        class TaskVerifier(VerificationEngine):
            def verify_output(self, _output, *, requirements=(), stage="result"):
                return object()

        result = ProviderAgent("agent", _Provider(), TaskVerifier()).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertFalse(result.verification.valid)

    def test_attack_205_verifier_failure_cannot_turn_provider_success_into_completion(self):
        class TaskVerifier(VerificationEngine):
            def verify_output(self, _output, *, requirements=(), stage="result"):
                raise RuntimeError("verification unavailable")

        result = ProviderAgent("agent", _Provider(output="trusted"), TaskVerifier()).run(self.task)
        self.assertNotEqual(result.status, "completed")
        self.assertEqual(result.status, "rejected")


if __name__ == "__main__":
    unittest.main()
