import unittest

from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime
from .provider import CallableProvider, ProviderRequest, ProviderResponse


class ProviderRuntimeTests(unittest.TestCase):
    def test_callable_provider_receives_structured_request(self):
        seen = []

        def execute(request: ProviderRequest):
            seen.append(request)
            return "provider-output"

        runtime = HypersynthRuntime(provider=CallableProvider(execute, provider_id="test-provider", model_id="test-model"))
        task = TaskSpec("provider-1", "analysis", "produce an answer", {"x": 1}, verification_requirements=("string",))
        result = runtime.run(task)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["results"][-1].output, "provider-output")
        self.assertEqual(seen[0].task_id, "provider-1:0")
        self.assertEqual(seen[0].objective, "produce an answer")

    def test_provider_metadata_is_not_allowed_to_change_output_identity(self):
        class BadProvider:
            provider_id = "good"

            def execute(self, request):
                return ProviderResponse("ok", provider_id="other")

        runtime = HypersynthRuntime(provider=BadProvider())
        task = TaskSpec("provider-2", "analysis", "answer", {})
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")

    def test_provider_exception_is_fail_closed(self):
        def execute(_request):
            raise RuntimeError("provider down")

        runtime = HypersynthRuntime(provider=CallableProvider(execute, provider_id="failing"))
        task = TaskSpec("provider-3", "analysis", "answer", {})
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
