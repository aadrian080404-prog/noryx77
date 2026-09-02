import unittest

from .memory import MemoryItem, MemoryStore


class SpoofedMemoryItem(MemoryItem):
    def __getattribute__(self, name):
        if name == "memory_id":
            return "attacker-id"
        if name == "content":
            return "attacker-content"
        if name == "kind":
            return "cloud"
        if name == "source":
            return "attacker-source"
        if name == "importance":
            return 1.0
        return super().__getattribute__(name)


class MemoryBoundary237To241Tests(unittest.TestCase):
    def test_attack237_memory_item_subclass_is_rejected_before_attribute_access(self):
        store = MemoryStore()
        item = SpoofedMemoryItem("m1", "good")
        with self.assertRaises(ValueError):
            store.put(item)
        self.assertEqual(len(store), 0)

    def test_attack238_canonical_memory_item_still_round_trips_authenticated(self):
        store = MemoryStore()
        item = MemoryItem("m1", {"answer": "trusted"}, source="local", importance=0.8)
        store.put(item)
        loaded = store.get("m1")
        self.assertIs(type(loaded), MemoryItem)
        self.assertEqual(loaded.content, {"answer": "trusted"})

    def test_attack239_authentication_encoder_rejects_spoofed_memory_subclass(self):
        with self.assertRaises(TypeError):
            MemoryStore._payload(SpoofedMemoryItem("m1", "good"))

    def test_attack240_retrieval_returns_canonical_isolated_copy(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", {"nested": [1]}, importance=0.5))
        result = store.retrieve()
        self.assertEqual(len(result), 1)
        self.assertIs(type(result[0]), MemoryItem)
        result[0].content["nested"].append(2)
        self.assertEqual(store.get("m1").content, {"nested": [1]})

    def test_attack241_corrupted_authenticated_state_cannot_be_bypassed_by_delete(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", "trusted"))
        store._items["m1"] = MemoryItem("m1", "tampered")
        with self.assertRaises(MemoryError):
            store.delete("m1")
        self.assertIn("m1", store._items)


if __name__ == "__main__":
    unittest.main()
