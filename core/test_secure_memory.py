import unittest

from .crypto import AuthenticatedCipher, InMemoryKeyProvider
from .memory import MemoryItem
from .secure_memory import EncryptedMemoryStore
from .secure_storage import StoredCiphertext


class EncryptedMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        provider = InMemoryKeyProvider({"memory-key": b"m" * 32, "other-key": b"o" * 32})
        self.store = EncryptedMemoryStore(
            AuthenticatedCipher(provider),
            namespace="long-term",
            max_items=4,
        )

    def test_round_trip_preserves_record(self):
        item = MemoryItem("m1", {"nested": [1, 2]}, kind="long_term", source="test", importance=0.8)
        self.store.put(item, key_id="memory-key")
        self.assertEqual(self.store.get("m1"), item)

    def test_bound_round_trip_preserves_execution(self):
        item = MemoryItem("m1", {"secret": "value"}, execution_id="exec-A")
        self.store.put(item, key_id="memory-key")
        self.assertEqual(self.store.get("m1", execution_id="exec-A"), item)
        self.assertIsNone(self.store.get("m1", execution_id="exec-B"))
        self.assertIsNone(self.store.get("m1"))

    def test_same_memory_id_can_coexist_across_owners(self):
        first = MemoryItem("shared", "A", principal_id="principal-A", agent_id="agent-A")
        second = MemoryItem("shared", "B", principal_id="principal-B", agent_id="agent-A")
        self.store.put(first, key_id="memory-key")
        self.store.put(second, key_id="memory-key")
        self.assertEqual(self.store.get("shared", principal_id="principal-A", agent_id="agent-A"), first)
        self.assertEqual(self.store.get("shared", principal_id="principal-B", agent_id="agent-A"), second)
        self.assertIsNone(self.store.get("shared"))

    def test_all_scope_dimensions_must_match(self):
        item = MemoryItem("m1", "secret", principal_id="p", agent_id="a", execution_id="e")
        self.store.put(item, key_id="memory-key")
        self.assertIsNone(self.store.get("m1", principal_id="p", execution_id="e"))
        self.assertIsNone(self.store.get("m1", principal_id="p", agent_id="a"))
        self.assertEqual(self.store.get("m1", principal_id="p", agent_id="a", execution_id="e"), item)

    def test_delete_is_scope_bound(self):
        first = MemoryItem("shared", "A", principal_id="p1")
        second = MemoryItem("shared", "B", principal_id="p2")
        self.store.put(first, key_id="memory-key")
        self.store.put(second, key_id="memory-key")
        self.assertFalse(self.store.delete("shared"))
        self.assertTrue(self.store.delete("shared", principal_id="p1"))
        self.assertEqual(self.store.get("shared", principal_id="p2"), second)

    def test_snapshot_contains_ciphertext_only(self):
        item = MemoryItem("m1", {"secret": "value"}, kind="suspended")
        self.store.put(item, key_id="memory-key")
        stored = self.store.snapshot_ciphertext()[0]
        self.assertNotIn(b"secret", stored.envelope.ciphertext)
        self.assertNotIn(b"value", stored.envelope.ciphertext)

    def test_record_id_swap_is_rejected_by_authenticated_storage(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        stored = self.store.snapshot_ciphertext()[0]
        self.store._store._records["m2"] = StoredCiphertext("m2", stored.envelope)
        with self.assertRaises(ValueError):
            self.store._store.get("m2")

    def test_namespace_swap_is_rejected(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        other = EncryptedMemoryStore(
            self.store._store.cipher,
            namespace="other-domain",
            max_items=4,
        )
        stored = self.store.snapshot_ciphertext()[0]
        other._store._records[stored.record_id] = stored
        with self.assertRaises(ValueError):
            other._store.get(stored.record_id)

    def test_wrong_key_epoch_is_rejected(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        provider = InMemoryKeyProvider({"memory-key": b"x" * 32})
        other = EncryptedMemoryStore(AuthenticatedCipher(provider), namespace="long-term")
        stored = self.store.snapshot_ciphertext()[0]
        other._store._records[stored.record_id] = stored
        with self.assertRaises(ValueError):
            other._store.get(stored.record_id)

    def test_non_json_content_is_rejected_before_persistence(self):
        item = MemoryItem("m1", object())
        with self.assertRaises(ValueError):
            self.store.put(item, key_id="memory-key")
        self.assertEqual(len(self.store), 0)

    def test_capacity_is_enforced(self):
        self.store.put(MemoryItem("m1", 1), key_id="memory-key")
        self.store.put(MemoryItem("m2", 2), key_id="memory-key")
        self.store.put(MemoryItem("m3", 3), key_id="memory-key")
        self.store.put(MemoryItem("m4", 4), key_id="memory-key")
        with self.assertRaises(MemoryError):
            self.store.put(MemoryItem("m5", 5), key_id="memory-key")


if __name__ == "__main__":
    unittest.main()
