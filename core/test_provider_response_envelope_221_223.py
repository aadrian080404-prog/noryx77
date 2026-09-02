import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .provider import ProviderResponse
from .verification import VerificationEngine


class SpoofedProviderResponse(ProviderResponse):
    def __getattribute__(self, name):
        if name == "provider_id":
            return "trusted"
        if name == "model_id":
            return "trusted-model"
        if name == "output":
            return "attacker-controlled"
        return super().__getattribute__(name)


class ResponseSpoofProvider:
    provider_id = "trusted"
    model_id = "trusted-model"

    def __init__(self, response):
        self.response = response

    def execute(self, request):
        return self.response


class ProviderResponseEnvelope221To223Tests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec(
            "provider-envelope",
            "general",
            "produce a result",
            {},
            {},
            ("string",),
            "normal",
        )
        self.verifier = VerificationEngine()

    def test_attack_221_rejects_provider_response_subclass(self):
        response = SpoofedProviderResponse("ok", "trusted", "trusted-model", {})
        result = ProviderAgent(
            "provider-agent", ResponseSpoofProvider(response), self.verifier
        ).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_provider_response")

    def test_attack_222_rejects_response_subclass_before_spoofed_identity_access(self):
        response = SpoofedProviderResponse("ok", "attacker", "attacker-model", {})
        result = ProviderAgent(
            "provider-agent", ResponseSpoofProvider(response), self.verifier
        ).run(self.task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.verification.reason, "malformed_provider_response")

    def test_attack_223_accepts_only_canonical_provider_response(self):
        response = ProviderResponse("ok", "trusted", "trusted-model", {})
        result = ProviderAgent(
            "provider-agent", ResponseSpoofProvider(response), self.verifier
        ).run(self.task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "ok")


if __name__ == "__main__":
    unittest.main()
