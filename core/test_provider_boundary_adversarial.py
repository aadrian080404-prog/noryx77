import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .provider import ProviderResponse
from .router import ResourceRouter
from .verification import VerificationEngine


class StubProvider:
    def __init__(self, provider_id="trusted", model_id="model-v1", output="ok"):
        self.provider_id = provider_id
        self.model_id = model_id
        self.output = output

    def execute(self, request):
        return ProviderResponse(self.output, self.provider_id, self.model_id, {})


class ProviderBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.task = TaskSpec(
            task_id="provider-boundary",
            task_type="research",
            objective="produce a verified result",
            input="controlled input",
            risk_class="normal",
        )

    def test_registered_provider_cannot_be_swapped_after_registration(self):
        trusted = StubProvider()
        attacker = StubProvider(provider_id="trusted", model_id="attacker-model", output="attacker")
        agent = ProviderAgent("provider-agent", trusted, self.verifier, model_class="large")
        router = ResourceRouter()
        router.register(agent)
        agent.provider = attacker
        with self.assertRaises(RuntimeError):
            router.route_for_task(self.task)

    def test_provider_id_mutation_is_detected_at_router_boundary(self):
        provider = StubProvider()
        agent = ProviderAgent("provider-agent", provider, self.verifier, model_class="large")
        router = ResourceRouter()
        router.register(agent)
        agent.provider_id = "attacker"
        with self.assertRaises(RuntimeError):
            router.available()

    def test_model_id_mutation_is_detected_at_router_boundary(self):
        provider = StubProvider()
        agent = ProviderAgent("provider-agent", provider, self.verifier, model_class="large")
        router = ResourceRouter()
        router.register(agent)
        agent.model_id = "attacker-model"
        with self.assertRaises(RuntimeError):
            router.get("provider-agent")


if __name__ == "__main__":
    unittest.main()
