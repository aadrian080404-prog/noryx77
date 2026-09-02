import unittest

from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime
from .provider import CallableProvider, ProviderRequest, ProviderResponse


class HypersynthRuntimeProviderTests(unittest.TestCase):
    def test_provider_runtime_defaults_to_research_capable_large_route(self):
        calls = []

        def execute(request: ProviderRequest):
            calls.append(request.task_id)
            return ProviderResponse("provider-output", "test-provider", "test-model", {})

        provider = CallableProvider(execute, provider_id="test-provider", model_id="test-model")
        runtime = HypersynthRuntime(provider=provider)
        task = TaskSpec("provider-research", "research", "analyze", "input")

        result = runtime.run(task)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls, ["provider-research:0"])
        self.assertEqual(result["results"][0].output, "provider-output")
        self.assertEqual(runtime.router.get("provider").model_class, "large")

    def test_provider_runtime_rejects_invalid_model_class(self):
        provider = CallableProvider(lambda _request: ProviderResponse("x", "p", "m", {}), provider_id="p", model_id="m")
        with self.assertRaises(ValueError):
            HypersynthRuntime(provider=provider, provider_model_class="invalid")


if __name__ == "__main__":
    unittest.main()
