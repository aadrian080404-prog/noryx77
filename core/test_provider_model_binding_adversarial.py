import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .provider import ProviderResponse
from .verification import VerificationEngine


class ModelSwapProvider:
    provider_id = "trusted-provider"
    model_id = "trusted-model"

    def execute(self, request):
        return ProviderResponse(
            output="verified output",
            provider_id=self.provider_id,
            model_id="attacker-model",
            metadata={},
        )


class ProviderModelBindingAdversarialTests(unittest.TestCase):
    def test_provider_cannot_claim_different_model_id(self):
        verifier = VerificationEngine()
        agent = ProviderAgent("provider-agent", ModelSwapProvider(), verifier)
        task = TaskSpec(
            task_id="provider-model-binding",
            task_type="research",
            objective="produce a verified result",
            input="controlled input",
            risk_class="normal",
        )

        result = agent.run(task)

        self.assertEqual(result.status, "rejected")
        self.assertIsNotNone(result.verification)
        self.assertEqual(result.verification.reason, "provider_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
