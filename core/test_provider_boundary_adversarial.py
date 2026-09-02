import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .provider import CallableProvider, ProviderResponse
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

    def test_callable_provider_rejects_blank_model_identity(self):
        with self.assertRaises(ValueError) as context:
            CallableProvider(lambda _request: "ok", provider_id="provider", model_id="   ")
        self.assertEqual(str(context.exception), "model_id_required")

    def test_provider_response_subclass_preserves_explicit_identity_validation(self):
        class ResponseSubclass(ProviderResponse):
            pass

        class Provider:
            provider_id = "provider"
            model_id = "model"

            def execute(self, _request):
                return ResponseSubclass("ok", provider_id="provider", model_id="model")

        agent = ProviderAgent("agent", Provider(), VerificationEngine())
        task = TaskSpec("boundary-1", "analysis", "answer", {}, verification_requirements=("string",))
        result = agent.run(task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "ok")

    def test_provider_identity_mutation_during_execution_fails_closed(self):
        class Provider:
            provider_id = "provider"
            model_id = "model"

            def execute(self, _request):
                self.provider_id = "attacker"
                self.model_id = "attacker-model"
                return ProviderResponse("ok", provider_id="attacker", model_id="attacker-model")

        provider = Provider()
        agent = ProviderAgent("agent", Provider(), VerificationEngine())
        task = TaskSpec("boundary-2", "analysis", "answer", {})
        result = agent.run(task)
        self.assertEqual(result.status, "rejected")

    def test_mutable_provider_output_is_isolated_from_provider_owned_object(self):
        output = {"answer": ["trusted"]}
        agent = ProviderAgent("agent", StubProvider(output=output), self.verifier)
        task = TaskSpec("boundary-3", "analysis", "answer", {})
        result = agent.run(task)
        self.assertEqual(result.status, "completed")
        result.output["answer"].append("consumer-mutation")
        self.assertEqual(output, {"answer": ["trusted"]})

    def test_non_copyable_provider_output_fails_closed(self):
        class NonCopyable:
            def __deepcopy__(self, memo):
                raise RuntimeError("no-copy")

        agent = ProviderAgent("agent", StubProvider(output=NonCopyable()), self.verifier)
        task = TaskSpec("boundary-4", "analysis", "answer", {})
        result = agent.run(task)
        self.assertEqual(result.status, "rejected")


if __name__ == "__main__":
    unittest.main()
