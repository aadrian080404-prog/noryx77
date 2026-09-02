import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .provider import ProviderResponse
from .verification import VerificationEngine


class _SpoofProvider:
    provider_id = "trusted"
    model_id = "model-a"

    def __init__(self, response_factory):
        self.response_factory = response_factory

    def execute(self, request):
        return self.response_factory(request)


class ProviderBoundary197To200Tests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.task = TaskSpec(
            "provider-boundary",
            "general",
            "return a bounded result",
            {},
            {},
            ("string",),
            "normal",
        )

    def test_attack_197_rejects_provider_id_spoof(self):
        provider = _SpoofProvider(
            lambda request: ProviderResponse("ok", provider_id="attacker", model_id="model-a", metadata={})
        )
        agent = ProviderAgent("provider-agent", provider, self.verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")

    def test_attack_198_rejects_model_id_spoof(self):
        provider = _SpoofProvider(
            lambda request: ProviderResponse("ok", provider_id="trusted", model_id="attacker-model", metadata={})
        )
        agent = ProviderAgent("provider-agent", provider, self.verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")

    def test_attack_199_rejects_malformed_provider_response(self):
        provider = _SpoofProvider(lambda request: {"output": "ok", "provider_id": "trusted", "model_id": "model-a"})
        agent = ProviderAgent("provider-agent", provider, self.verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")

    def test_attack_200_rejects_invalid_provider_metadata(self):
        provider = _SpoofProvider(
            lambda request: ProviderResponse("ok", provider_id="trusted", model_id="model-a", metadata="not-a-mapping")
        )
        agent = ProviderAgent("provider-agent", provider, self.verifier)
        result = agent.run(self.task)
        self.assertEqual(result.status, "rejected")


if __name__ == "__main__":
    unittest.main()
