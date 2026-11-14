import unittest

from core.contracts import TaskSpec
from core.hypersynth_runtime import HypersynthRuntime
from core.llm.agent import LLMBackedAgent
from core.verification import VerificationEngine
from core.router import ResourceRouter


class FakeModel:
    name = "frontier-test-model"
    capabilities = frozenset({"text", "reasoning", "chat"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        return "verified frontier response"


class FrontierIntegrationWaveTests(unittest.TestCase):
    def test_capability_registry_contains_frontier_surface(self):
        runtime = HypersynthRuntime()
        names = runtime.tool_executor.capabilities.names()
        for name in ("web_research", "chess_analyze", "payments", "flights", "insurance"):
            self.assertIn(name, names)

    def test_web_capability_rejects_cleartext(self):
        runtime = HypersynthRuntime()
        handler = runtime.tool_executor.capabilities.resolve("web_research")
        with self.assertRaises(ValueError):
            handler("http://example.com", {})

    def test_external_providers_fail_closed(self):
        runtime = HypersynthRuntime()
        for name in ("payments", "flights", "insurance"):
            handler = runtime.tool_executor.capabilities.resolve(name)
            with self.assertRaises(RuntimeError):
                handler("operation", {})

    def test_primary_identity_metadata(self):
        from core.identity import AgentIdentityAuthority
        identity, _ = AgentIdentityAuthority.generate("noryx7-llm")
        agent = LLMBackedAgent(FakeModel(), verifier=VerificationEngine(), identity=identity)
        description = agent.describe()
        self.assertEqual(description["agent_id"], "noryx7-llm")
        self.assertEqual(description["creator"], "Adrian Aristodemo")
        self.assertIn("web_research", description["capabilities"])


if __name__ == "__main__":
    unittest.main()
