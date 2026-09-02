import unittest

from .actions import ActionDecision
from .agents import DeterministicAgent
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .router import ResourceRouter
from .verification import VerificationEngine


class MutatingActionGate:
    def __init__(self, agent):
        self.agent = agent
        self.calls = 0

    def authorize(self, _action, calls_used=0):
        self.calls += 1
        self.agent.model_class = "frontier"
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))


class HypersynthExecutionRevalidationAdversarialTests(unittest.TestCase):
    def test_mutation_after_action_authorization_is_rejected_before_agent_run(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        agent = DeterministicAgent(verifier)
        agent.agent_id = "trusted"
        router.register(agent)
        gate = MutatingActionGate(agent)
        kernel = Hypersynth(verifier, router, action_gate=gate)
        task = TaskSpec("execution-toctou", "research", "analyze", "input")

        result = kernel.run(task)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "execution")
        self.assertEqual(result["verification"].reason, "agent_registration_runtime_failure")
        self.assertEqual(gate.calls, 1)


if __name__ == "__main__":
    unittest.main()
