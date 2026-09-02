import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter
from .verification import VerificationEngine


class RouterRegistrationBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.router = ResourceRouter()
        self.verifier = VerificationEngine()
        self.agent = DeterministicAgent(self.verifier)
        self.router.register(self.agent)
        self.task = TaskSpec("router-boundary", "research", "answer", {})

    def test_validate_registered_accepts_untampered_identity(self):
        self.router.validate_registered(self.agent)

    def test_validate_registered_rejects_replacement_object(self):
        replacement = DeterministicAgent(self.verifier)
        replacement.agent_id = self.agent.agent_id
        with self.assertRaises(LookupError):
            self.router.validate_registered(replacement)

    def test_validate_registered_rejects_metadata_mutation(self):
        self.agent.model_class = "frontier"
        with self.assertRaises(RuntimeError):
            self.router.validate_registered(self.agent)

    def test_validate_registered_rejects_provider_binding_mutation(self):
        original = getattr(self.agent, "provider", None)
        self.agent.provider = object()
        with self.assertRaises(RuntimeError):
            self.router.validate_registered(self.agent)
        self.agent.provider = original

    def test_route_for_task_remains_fail_closed_after_tampering(self):
        self.agent.model_class = "frontier"
        with self.assertRaises(RuntimeError):
            self.router.route_for_task(self.task)


if __name__ == "__main__":
    unittest.main()
