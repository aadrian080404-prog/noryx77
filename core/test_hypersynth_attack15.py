import unittest

from .memory import MemoryItem, MemoryStore


class Attack15Tests(unittest.TestCase):
    def test_put_isolates_mutable_input(self):
        payload = {"value": ["original"]}
        store = MemoryStore()
        store.put(MemoryItem("m1", payload))
        payload["value"].append("forged")
        self.assertEqual(store.get("m1").content, {"value": ["original"]})

    def test_get_returns_isolated_copy(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", {"value": ["original"]}))
        retrieved = store.get("m1")
        retrieved.content["value"].append("forged")
        self.assertEqual(store.get("m1").content, {"value": ["original"]})

    def test_list_returns_isolated_items(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", {"value": ["original"]}))
        listed = store.list()
        listed[0].content["value"].append("forged")
        self.assertEqual(store.get("m1").content, {"value": ["original"]})

    def test_whitespace_memory_id_is_rejected(self):
        with self.assertRaises(ValueError):
            MemoryStore().put(MemoryItem("   ", "content"))


if __name__ == "__main__":
    unittest.main()
