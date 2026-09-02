import unittest

from .memory import MemoryItem, MemoryStore


class MemoryBoundary242To244Tests(unittest.TestCase):
    def test_attack242_legacy_authentication_without_schema_version_is_rejected(self):
        store = MemoryStore()
        item = MemoryItem("m1", "trusted", source="system")
        store._items[item.memory_id] = item
        legacy_payload = {
            "memory_id": item.memory_id,
            "content": item.content,
            "kind": item.kind,
            "source": item.source,
            "importance": float(item.importance),
        }
        store._auth[item.memory_id] = store._crypto.digest("memory", legacy_payload)
        with self.assertRaises(MemoryError):
            store.get(item.memory_id)

    def test_attack243_authenticated_entry_cannot_replay_across_store_namespace(self):
        crypto_key = b"K" * 32
        from .crypto import CryptoIntegrity

        crypto = CryptoIntegrity(crypto_key)
        source = MemoryStore(crypto=crypto)
        target = MemoryStore(crypto=crypto)
        item = MemoryItem("m1", "trusted", source="system")
        source.put(item)

        target._items[item.memory_id] = source._items[item.memory_id]
        target._auth[item.memory_id] = source._auth[item.memory_id]

        with self.assertRaises(MemoryError):
            target.get(item.memory_id)

    def test_attack244_normal_authenticated_entry_still_verifies_after_namespace_binding(self):
        crypto_key = b"K" * 32
        from .crypto import CryptoIntegrity

        store = MemoryStore(crypto=CryptoIntegrity(crypto_key))
        store.put(MemoryItem("m1", {"value": "trusted"}, kind="long_term", source="system", importance=0.9))
        result = store.get("m1")
        self.assertEqual(result.content, {"value": "trusted"})
        self.assertEqual(result.kind, "long_term")
        self.assertEqual(result.source, "system")


if __name__ == "__main__":
    unittest.main()
