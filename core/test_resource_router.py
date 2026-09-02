import unittest

from .agents import DeterministicAgent, ProviderAgent
from .contracts import TaskSpec
from .provider import CallableProvider
from .router import ResourceRouter
from .verification import VerificationEngine


class ResourceRouterTests(unittest.TestCase):
    def provider_agent(self, agent_id, model_class):
        provider = CallableProvider(lambda request: "ok", provider_id=agent_id, model_id=agent_id + "-model")
        return ProviderAgent(agent_id, provider, model_class=model_class)

    def test_selects_smallest_sufficient_model_class(self):
        router = ResourceRouter()
        router.register(self.provider_agent("small", "small"))
        router.register(self.provider_agent("medium", "medium"))
        router.register(self.provider_agent("large", "large"))
        task = TaskSpec("t", "analysis", "answer", {})
        self.assertEqual(router.route_for_task(task).agent_id, "medium")

    def test_unknown_task_type_uses_medium_requirement(self):
        router = ResourceRouter()
        router.register(self.provider_agent("micro", "micro"))
        router.register(self.provider_agent("medium", "medium"))
        task = TaskSpec("t", "custom", "answer", {})
        self.assertEqual(router.route_for_task(task).agent_id, "medium")

    def test_insufficient_resources_fail_closed(self):
        router = ResourceRouter()
        router.register(DeterministicAgent(VerificationEngine()))
        task = TaskSpec("t", "research", "answer", {})
        with self.assertRaises(LookupError):
            router.route_for_task(task)

    def test_equal_model_class_uses_stable_agent_id_tiebreak(self):
        router = ResourceRouter()
        router.register(self.provider_agent("zeta", "medium"))
        router.register(self.provider_agent("alpha", "medium"))
        task = TaskSpec("t", "analysis", "answer", {})
        self.assertEqual(router.route_for_task(task).agent_id, "alpha")

    def test_invalid_routing_metadata_is_rejected(self):
        class BadAgent:
            agent_id = "bad"
            model_class = "unknown"
            capabilities = ()
            def run(self, task):
                pass

        router = ResourceRouter()
        with self.assertRaises(ValueError):
            router.register(BadAgent())


if __name__ == "__main__":
    unittest.main()
