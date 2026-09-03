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

    def test_router_rejects_duplicate_agent_identity(self):
        router = ResourceRouter()
        router.register(DeterministicAgent())
        with self.assertRaises(ValueError):
            router.register(DeterministicAgent())
        self.assertEqual(router.available(), ("deterministic",))

    def test_memory_is_bounded_and_replaceable(self):
        store = MemoryStore(max_items=2)
        first = MemoryItem("m1", "hello", "working", "test", 0.8)
        second = MemoryItem("m2", "world", "suspended", "test", 0.7)
        store.put(first)
        store.put(second)
        self.assertEqual(store.get("m1"), first)
        replacement = MemoryItem("m1", "updated", "working", "test", 0.9)
        store.put(replacement)
        self.assertEqual(store.get("m1"), replacement)
        with self.assertRaises(MemoryError):
            store.put(MemoryItem("m3", "overflow", "working", "test", 0.5))
        self.assertTrue(store.delete("m1"))
        self.assertIsNone(store.get("m1"))
