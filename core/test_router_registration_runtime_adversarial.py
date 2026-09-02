import unittest

from .agents import DeterministicAgent
from .router import ResourceRouter
from .verification import VerificationEngine


class RouterRegistrationRuntimeAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.agent = DeterministicAgent(self.verifier)
        self.agent.agent_id = "trusted"
        self.router.register(self.agent)

    def test_registered_agent_passes_runtime_revalidation(self):
        self.router.validate_registered(self.agent)

    def test_model_class_tampering_is_rejected_at_runtime(self):
        self.agent.model_class = "frontier"
        with self.assertRaises(RuntimeError):
            self.router.validate_registered(self.agent)

    def test_capability_tampering_is_rejected_at_runtime(self):
        self.agent.capabilities = ("forged",)
        with self.assertRaises(RuntimeError):
            self.router.validate_registered(self.agent)

    def test_provider_binding_tampering_is_rejected_at_runtime(self):
        self.agent.provider = object()
        with self.assertRaises(RuntimeError):
            self.router.validate_registered(self.agent)

    def test_replacement_object_is_rejected_at_runtime(self):
        replacement = DeterministicAgent(self.verifier)
        replacement.agent_id = "trusted"
        with self.assertRaises(LookupError):
            self.router.validate_registered(replacement)


if __name__ == "__main__":
    unittest.main()
