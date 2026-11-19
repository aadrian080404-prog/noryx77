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

    def test_principal_and_agent_scopes_are_independent(self):
        store = MemoryStore()
        store.put(MemoryItem("same", "A", principal_id="principal-A", agent_id="agent-A"))
        store.put(MemoryItem("same", "B", principal_id="principal-B", agent_id="agent-A"))
        store.put(MemoryItem("same", "C", principal_id="principal-A", agent_id="agent-B"))
        self.assertEqual(store.get("same", principal_id="principal-A", agent_id="agent-A").content, "A")
        self.assertEqual(store.get("same", principal_id="principal-B", agent_id="agent-A").content, "B")
        self.assertEqual(store.get("same", principal_id="principal-A", agent_id="agent-B").content, "C")
        self.assertIsNone(store.get("same", principal_id="principal-B", agent_id="agent-B"))

    def test_unscoped_reads_only_return_explicit_global_memory(self):
        store = MemoryStore()
        store.put(MemoryItem("global", "shared"))
        store.put(MemoryItem("private", "secret", principal_id="principal-A"))
        self.assertEqual(store.get("global").content, "shared")
        self.assertIsNone(store.get("private"))
        self.assertEqual([x.memory_id for x in store.list()], ["global"])

    def test_scope_dimensions_must_match_exactly(self):
        store = MemoryStore()
        store.put(MemoryItem("bound", "secret", principal_id="p", execution_id="e"))
        self.assertIsNone(store.get("bound", principal_id="p"))
        self.assertIsNone(store.get("bound", execution_id="e"))
        self.assertEqual(store.get("bound", principal_id="p", execution_id="e").content, "secret")

    def test_delete_is_scope_bound(self):
        store = MemoryStore()
        store.put(MemoryItem("same", "A", principal_id="p1"))
        store.put(MemoryItem("same", "B", principal_id="p2"))
        self.assertFalse(store.delete("same"))
        self.assertTrue(store.delete("same", principal_id="p1"))
        self.assertEqual(store.get("same", principal_id="p2").content, "B")

    def test_invalid_identity_scope_is_rejected(self):
        store = MemoryStore()
        with self.assertRaises(ValueError):
            store.put(MemoryItem("a", "A", principal_id="x" * 1025))
        with self.assertRaises(ValueError):
            store.put(MemoryItem("b", "B", agent_id="x" * 1025))


    def test_surrogate_code_points_are_rejected_without_encoding_exceptions(self):
        store = MemoryStore()
        invalid = "\ud800"
        with self.assertRaises(ValueError):
            store.put(MemoryItem("valid-id", "x", principal_id=invalid))
        with self.assertRaises(ValueError):
            store.put(MemoryItem("valid-id", "x", agent_id=invalid))
        with self.assertRaises(ValueError):
            store.put(MemoryItem("valid-id", "x", execution_id=invalid))
        with self.assertRaises(ValueError):
            store.put(MemoryItem(invalid, "x"))
        self.assertIsNone(store.get(invalid))
        self.assertIsNone(store.get("valid-id", principal_id=invalid))
        self.assertEqual(store.list(agent_id=invalid), ())


if __name__ == "__main__":
    unittest.main()
