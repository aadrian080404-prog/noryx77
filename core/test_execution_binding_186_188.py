import unittest

from .agents import ProviderAgent
from .contracts import AgentResult, ProviderResponse, TaskSpec, VerificationResult
from .provider import CallableProvider
from .router import ResourceRouter


class _Agent:
    agent_id = "a"
    model_class = "medium"
    capabilities = ()
    capacity_exempt = False

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id, "completed", output="ok", verification=VerificationResult(True, "result", "ok"))


class _Verifier:
    def verify_task(self, task):
        return VerificationResult(True, "contract", "ok")

    def verify_output(self, output, requirements=(), stage="result"):
        return VerificationResult(output is not None, stage, "ok" if output is not None else "bad")


class ExecutionBinding186To188Tests(unittest.TestCase):
    def test_186_router_rejects_registered_agent_run_substitution(self):
        router = ResourceRouter()
        agent = _Agent()
        router.register(agent)
        agent.run = lambda task: AgentResult(agent.agent_id, task.task_id, "completed", output="tampered", verification=VerificationResult(True, "result", "ok"))
        with self.assertRaisesRegex(RuntimeError, "registered_agent_metadata_mutated"):
            router.validate_registered(agent)

    def test_187_provider_agent_rejects_execute_substitution(self):
        calls = []

        def original(request):
            calls.append("original")
            return ProviderResponse("safe", "model", "ok")

        def malicious(request):
            calls.append("malicious")
            return ProviderResponse("safe", "model", "tampered")

        provider = CallableProvider(original, provider_id="safe", model_id="model")
        agent = ProviderAgent("a", provider, _Verifier())
        provider.execute = malicious
        result = agent.run(TaskSpec("t187", "general", "objective"))
        self.assertEqual(calls, [])
        self.assertEqual(result.status, "rejected")

    def test_188_provider_agent_uses_bound_execute_even_if_attribute_changes_during_call(self):
        calls = []
        provider = None

        def original(request):
            calls.append("original")
            provider.execute = lambda request: calls.append("replacement") or ProviderResponse("safe", "model", "tampered")
            return ProviderResponse("safe", "model", "ok")

        provider = CallableProvider(original, provider_id="safe", model_id="model")
        agent = ProviderAgent("a", provider, _Verifier())
        result = agent.run(TaskSpec("t188", "general", "objective"))
        self.assertEqual(calls, ["original"])
        self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
