import unittest

from .agents import Agent, DeterministicAgent
from .router import ResourceRouter


class Attack18Tests(unittest.TestCase):
    def test_non_agent_registration_is_rejected(self):
        router = ResourceRouter()
        with self.assertRaisesRegex(TypeError, "invalid_agent"):
            router.register(object())

    def test_invalid_agent_id_is_rejected(self):
        router = ResourceRouter()
        agent = DeterministicAgent()
        agent.agent_id = "   "
        with self.assertRaisesRegex(ValueError, "agent_id required"):
            router.register(agent)

    def test_duplicate_agent_identity_is_rejected(self):
        router = ResourceRouter()
        router.register(DeterministicAgent())
        duplicate = DeterministicAgent()
        with self.assertRaisesRegex(ValueError, "duplicate_agent_id"):
            router.register(duplicate)

    def test_route_identity_mismatch_fails_closed(self):
        router = ResourceRouter()
        agent = DeterministicAgent()
        router.register(agent)
        agent.agent_id = "mutated"
        with self.assertRaisesRegex(LookupError, "agent_identity_mismatch"):
            router.route("deterministic")

    def test_get_identity_mismatch_fails_closed(self):
        router = ResourceRouter()
        agent = DeterministicAgent()
        router.register(agent)
        agent.agent_id = "mutated"
        with self.assertRaisesRegex(LookupError, "agent_identity_mismatch"):
            router.get("deterministic")

    def test_malformed_preferred_identity_is_rejected(self):
        router = ResourceRouter()
        router.register(DeterministicAgent())
        with self.assertRaisesRegex(ValueError, "invalid_preferred_agent_id"):
            router.route("")
        with self.assertRaisesRegex(ValueError, "invalid_preferred_agent_id"):
            router.route(123)

    def test_available_fails_closed_on_registered_identity_mutation(self):
        router = ResourceRouter()
        agent = DeterministicAgent()
        router.register(agent)
        agent.agent_id = "mutated"
        with self.assertRaisesRegex(RuntimeError, "agent_identity_mismatch"):
            router.available()

    def test_available_returns_snapshot(self):
        router = ResourceRouter()
        router.register(DeterministicAgent())
        available = router.available()
        self.assertEqual(available, ("deterministic",))
        self.assertIsInstance(available, tuple)

    def test_base_agent_identity_is_valid(self):
        router = ResourceRouter()
        router.register(Agent())
        self.assertEqual(router.default_id(), "base")


if __name__ == "__main__":
    unittest.main()
