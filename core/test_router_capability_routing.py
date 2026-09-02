import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter
from .verification import VerificationEngine


class CapabilityRoutingTests(unittest.TestCase):
    def agent(self, agent_id, model_class, capabilities=()):
        agent = DeterministicAgent(VerificationEngine())
        agent.agent_id = agent_id
        agent.model_class = model_class
        agent.capabilities = tuple(capabilities)
        return agent

    def test_required_capability_filters_underqualified_agent(self):
        router = ResourceRouter()
        router.register(self.agent("small-unqualified", "large"))
        router.register(self.agent("capable", "large", ("research",)))
        task = TaskSpec(
            "capability-1", "research", "research objective", "input",
            constraints={"required_capabilities": ("research",)},
        )
        self.assertEqual(router.route_for_task(task).agent_id, "capable")

    def test_missing_required_capability_fails_closed(self):
        router = ResourceRouter()
        router.register(self.agent("large", "large", ("analysis",)))
        task = TaskSpec(
            "capability-2", "research", "research objective", "input",
            constraints={"required_capabilities": ("research",)},
        )
        with self.assertRaises(LookupError):
            router.route_for_task(task)

    def test_malformed_capability_requirement_is_rejected(self):
        router = ResourceRouter()
        router.register(self.agent("large", "large", ("research",)))
        task = TaskSpec(
            "capability-3", "research", "research objective", "input",
            constraints={"required_capabilities": ["research"]},
        )
        with self.assertRaises(ValueError):
            router.route_for_task(task)

    def test_duplicate_capability_requirement_is_rejected(self):
        router = ResourceRouter()
        router.register(self.agent("large", "large", ("research",)))
        task = TaskSpec(
            "capability-4", "research", "research objective", "input",
            constraints={"required_capabilities": ("research", "research")},
        )
        with self.assertRaises(ValueError):
            router.route_for_task(task)


if __name__ == "__main__":
    unittest.main()
