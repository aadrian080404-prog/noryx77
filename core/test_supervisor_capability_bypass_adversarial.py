import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class SupervisorCapabilityBypassAdversarialTests(unittest.TestCase):
    def test_preferred_underqualified_agent_cannot_bypass_capability_gate(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        agent = DeterministicAgent(verifier)
        agent.agent_id = "preferred"
        agent.model_class = "large"
        agent.capabilities = ("analysis",)
        router.register(agent)
        supervisor = AgentSupervisor(router, verifier)
        task = TaskSpec(
            "preferred-capability", "research", "research objective", "input",
            constraints={"required_capabilities": ("research",)},
        )

        selected, decision = supervisor.select(task, preferred="preferred")

        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "resource_missing_required_capability")


if __name__ == "__main__":
    unittest.main()
