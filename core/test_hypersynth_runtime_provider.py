import unittest

from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime
from .provider import CallableProvider, ProviderRequest


class HypersynthRuntimeProviderTests(unittest.TestCase):
    def test_provider_runtime_defaults_to_research_capable_large_route(self):
        calls = []

        def execute(request: ProviderRequest):
            calls.append(request.task_id)
            return "provider-output"

        provider = CallableProvider(execute, provider_id="test-provider", model_id="test-model")
        runtime = HypersynthRuntime(provider=provider)
        task = TaskSpec("provider-research", "research", "analyze", "input")

        result = runtime.run(task)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls, ["provider-research:0"])
        self.assertEqual(result["results"][0].output, "provider-output")
        self.assertEqual(runtime.router.get("provider").model_class, "large")

    def test_provider_runtime_defaults_to_full_nine_stage_attested_execution(self):
        provider = CallableProvider(lambda _request: "attested", provider_id="p", model_id="m")
        runtime = HypersynthRuntime(provider=provider)
        result = runtime.run(TaskSpec("provider-attested", "research", "analyze", "input"))

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["attestation_verified"])
        self.assertTrue(result["continuity_verified"])
        self.assertTrue(result["export_manifest_verified"])
        self.assertTrue(result["final_integrity_verified"])
        self.assertEqual(
            tuple(item.stage for item in result["attestations"]),
            runtime.attested_kernel.STAGE_ORDER,
        )
        self.assertEqual(len(result["attestations"]), 9)
        self.assertEqual(len(result["continuity_records"]), 9)

    def test_provider_runtime_accepts_explicit_model_class_and_capabilities(self):
        provider = CallableProvider(lambda _request: "x", provider_id="p", model_id="m")
        runtime = HypersynthRuntime(provider=provider, provider_model_class="frontier", provider_capabilities=("reasoning", "research"))
        agent = runtime.router.get("provider")
        self.assertEqual(agent.model_class, "frontier")
        self.assertEqual(agent.capabilities, ("reasoning", "research"))

    def test_provider_runtime_rejects_invalid_model_class(self):
        provider = CallableProvider(lambda _request: "x", provider_id="p", model_id="m")
        with self.assertRaises(ValueError):
            HypersynthRuntime(provider=provider, provider_model_class="invalid")


if __name__ == "__main__":
    unittest.main()
