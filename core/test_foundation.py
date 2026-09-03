import unittest

from .agents import DeterministicAgent
from .contracts import ActionSpec, TaskSpec
from .memory import MemoryItem, MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .runtime import NORYXRuntime
from .verification import VerificationEngine


class FoundationTests(unittest.TestCase):
    def test_task_contract_and_runtime(self):
        task = TaskSpec("t1", "research", "inspect", "input")
        result = NORYXRuntime().run(task)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["results"])
        self.assertTrue(result["results"][-1].verification.valid)

    def test_unknown_risk_is_rejected(self):
        task = TaskSpec("t1", "x", "y", "z", risk_class="unknown")
        self.assertFalse(VerificationEngine().verify_task(task).valid)

    def test_policy_fails_closed_for_unknown_and_high_risk(self):
        policy = PolicyEngine()
        self.assertFalse(policy.evaluate(ActionSpec("a", "unknown")).get("allowed"))
        self.assertFalse(policy.evaluate(ActionSpec("b", "financial")).get("allowed"))

    def test_router_requires_explicit_route_when_ambiguous(self):
        router = ResourceRouter()
        router.register(DeterministicAgent())
        self.assertEqual(router.route().agent_id, "deterministic")

    def test_memory_is_bounded_and_replaceable(self):
        store = MemoryStore()
        item = MemoryItem("m1", "hello", "postit", "test", 0.8)
        store.put(item)
        self.assertEqual(store.get("m1"), item)
        self.assertTrue(store.delete("m1"))
        self.assertIsNone(store.get("m1"))


if __name__ == "__main__":
    unittest.main()
