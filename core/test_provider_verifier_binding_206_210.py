import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec, VerificationResult
from .provider import ProviderResponse
from .verification import VerificationEngine


class _Provider:
    provider_id = "trusted"
    model_id = "model-a"

    def __init__(self, on_execute=None):
        self.on_execute = on_execute

    def execute(self, _request):
        if self.on_execute is not None:
            self.on_execute()
        return ProviderResponse("ok", provider_id=self.provider_id, model_id=self.model_id, metadata={})


class _PermissiveVerifier(VerificationEngine):
    def verify_task(self, _task):
        return VerificationResult(True, "contract", "accepted")

    def verify_output(self, _output, *, requirements=(), stage="result"):
        return VerificationResult(True, stage, "accepted")


class ProviderVerifierBinding206To210Tests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec(
            "provider-verifier-binding",
            "analysis",
            "answer",
            {},
            {},
            ("string",),
            "normal",
        )

    def test_attack_206_verifier_replacement_during_task_verification_is_rejected(self):
        agent = None

        class MutatingVerifier(VerificationEngine):
            def verify_task(self, task):
                agent.verifier = _PermissiveVerifier()
                return super().verify_task(task)

        verifier = MutatingVerifier()
        agent = ProviderAgent("agent", _Provider(), verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "verifier_binding_changed")

    def test_attack_207_verifier_replacement_during_provider_execution_is_rejected(self):
        agent = None
        verifier = VerificationEngine()

        def replace_verifier():
            agent.verifier = _PermissiveVerifier()

        agent = ProviderAgent("agent", _Provider(on_execute=replace_verifier), verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "verifier_binding_changed")

    def test_attack_208_output_verifier_method_swap_during_execution_is_rejected(self):
        verifier = VerificationEngine()

        def replacement_output(_output, *, requirements=(), stage="result"):
            return VerificationResult(True, stage, "forged")

        def mutate_method():
            verifier.verify_output = replacement_output

        agent = ProviderAgent("agent", _Provider(on_execute=mutate_method), verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "verifier_binding_changed")

    def test_attack_209_task_verifier_mutation_after_task_gate_cannot_change_bound_output_verifier(self):
        verifier = VerificationEngine()

        def replacement_task(_task):
            return VerificationResult(True, "contract", "forged")

        def mutate_method():
            verifier.verify_task = replacement_task

        agent = ProviderAgent("agent", _Provider(on_execute=mutate_method), verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.verification.valid)

    def test_attack_210_bound_verifier_methods_are_used_for_final_output_check(self):
        verifier = VerificationEngine()
        agent = ProviderAgent("agent", _Provider(), verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "completed")
        self.assertIsInstance(result.verification, VerificationResult)
        self.assertTrue(result.verification.valid)


if __name__ == "__main__":
    unittest.main()
