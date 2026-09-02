import unittest

from .memory import MemoryItem, MemoryStore


class MemoryRetrievalTests(unittest.TestCase):
    def test_retrieve_filters_source_and_sorts_deterministically(self):
        store = MemoryStore()
        store.put(MemoryItem("b", "low", source="task", importance=0.2))
        store.put(MemoryItem("a", "high", source="task", importance=0.9))
        store.put(MemoryItem("c", "other", source="other", importance=1.0))

        result = store.retrieve(source="task")
        self.assertEqual(tuple(item.memory_id for item in result), ("a", "b"))
        self.assertEqual(result[0].content, "high")

    def test_retrieve_filters_kind_and_limit(self):
        store = MemoryStore()
        store.put(MemoryItem("a", "one", kind="working", importance=0.9))
        store.put(MemoryItem("b", "two", kind="long_term", importance=0.8))
        store.put(MemoryItem("c", "three", kind="long_term", importance=0.7))

        result = store.retrieve(kind="long_term", limit=1)
        self.assertEqual(tuple(item.memory_id for item in result), ("b",))

    def test_retrieve_returns_isolated_copies(self):
        store = MemoryStore()
        store.put(MemoryItem("a", {"value": [1]}, source="task"))
        result = store.retrieve(source="task")
        result[0].content["value"].append(2)
        self.assertEqual(store.get("a").content, {"value": [1]})

    def test_retrieve_fails_closed_on_tampering(self):
        store = MemoryStore()
        store.put(MemoryItem("a", "trusted", source="task"))
        store._items["a"] = MemoryItem("a", "tampered", source="task")
        with self.assertRaisesRegex(MemoryError, "memory_integrity_failure"):
            store.retrieve(source="task")

    def test_invalid_retrieval_filters_are_rejected(self):
        store = MemoryStore()
        with self.assertRaises(ValueError):
            store.retrieve(source=123)
        with self.assertRaises(ValueError):
            store.retrieve(kind="invalid")
        with self.assertRaises(ValueError):
            store.retrieve(limit=0)


if __name__ == "__main__":
    unittest.main()
