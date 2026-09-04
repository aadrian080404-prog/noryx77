import unittest

from .memory import MemoryItem, MemoryStore


class MemoryBoundaryTests(unittest.TestCase):
    def test_bound_record_cannot_cross_execution(self):
        store = MemoryStore()
        store.put(MemoryItem("same-task", "A", execution_id="exec-A"))
        self.assertEqual(store.get("same-task", execution_id="exec-A").content, "A")
        self.assertIsNone(store.get("same-task", execution_id="exec-B"))

    def test_bound_lookup_cannot_fall_back_to_unbound_record(self):
        store = MemoryStore()
        store.put(MemoryItem("task", "legacy"))
        self.assertIsNone(store.get("task", execution_id="exec-A"))

    def test_bound_list_is_execution_scoped(self):
        store = MemoryStore()
        store.put(MemoryItem("a", "A", execution_id="exec-A"))
        store.put(MemoryItem("b", "B", execution_id="exec-B"))
        store.put(MemoryItem("legacy", "L"))
        self.assertEqual([x.memory_id for x in store.list(execution_id="exec-A")], ["a"])
        self.assertEqual([x.memory_id for x in store.list(execution_id="exec-B")], ["b"])

    def test_invalid_execution_context_is_denied(self):
        store = MemoryStore()
        store.put(MemoryItem("a", "A", execution_id="exec-A"))
        self.assertIsNone(store.get("a", execution_id=""))
        self.assertEqual(store.list(execution_id=""), ())

    def test_execution_identity_is_validated_on_write(self):
        store = MemoryStore()
        with self.assertRaises(ValueError):
            store.put(MemoryItem("a", "A", execution_id="x" * 257))

    def test_memory_id_collision_cannot_replace_another_execution(self):
        store = MemoryStore()
        store.put(MemoryItem("shared", "A", execution_id="exec-A"))
        with self.assertRaisesRegex(ValueError, "memory_id_execution_collision"):
            store.put(MemoryItem("shared", "attacker", execution_id="exec-B"))
        self.assertEqual(store.get("shared", execution_id="exec-A").content, "A")
        self.assertIsNone(store.get("shared", execution_id="exec-B"))

    def test_memory_get_and_list_return_deep_copies(self):
        store = MemoryStore()
        payload = {"nested": ["original"]}
        store.put(MemoryItem("mutable", payload, execution_id="exec-A"))
        returned = store.get("mutable", execution_id="exec-A")
        returned.content["nested"].append("tampered")
        listed = store.list(execution_id="exec-A")
        self.assertEqual(listed[0].content, {"nested": ["original"]})


if __name__ == "__main__":
    unittest.main()
