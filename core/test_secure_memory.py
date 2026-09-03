import unittest

from .crypto import AuthenticatedCipher, InMemoryKeyProvider
from .memory import MemoryItem
from .secure_memory import EncryptedMemoryStore


class EncryptedMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        provider = InMemoryKeyProvider({"memory-key": b"m" * 32, "other-key": b"o" * 32})
        self.store = EncryptedMemoryStore(
            AuthenticatedCipher(provider),
            namespace="long-term",
            max_items=2,
        )

    def test_round_trip_preserves_record(self):
        item = MemoryItem("m1", {"nested": [1, 2]}, kind="long_term", source="test", importance=0.8)
        self.store.put(item, key_id="memory-key")
        self.assertEqual(self.store.get("m1"), item)

    def test_snapshot_contains_ciphertext_only(self):
        item = MemoryItem("m1", {"secret": "value"}, kind="suspended")
        self.store.put(item, key_id="memory-key")
        stored = self.store.snapshot_ciphertext()[0]
        self.assertNotIn(b"secret", stored.envelope.ciphertext)
        self.assertNotIn(b"value", stored.envelope.ciphertext)

    def test_record_id_swap_is_rejected(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        stored = self.store.snapshot_ciphertext()[0]
        with self.assertRaises(ValueError):
            self.store._store._records["m2"] = type(stored)("m2", stored.envelope)
            self.store.get("m2")

    def test_namespace_swap_is_rejected(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        other = EncryptedMemoryStore(
            self.store._store.cipher,
            namespace="other-domain",
            max_items=2,
        )
        other._store._records["m1"] = self.store.snapshot_ciphertext()[0]
        with self.assertRaises(ValueError):
            other.get("m1")

    def test_wrong_key_epoch_is_rejected(self):
        item = MemoryItem("m1", {"value": 1})
        self.store.put(item, key_id="memory-key")
        provider = InMemoryKeyProvider({"memory-key": b"x" * 32})
        other = EncryptedMemoryStore(AuthenticatedCipher(provider), namespace="long-term")
        other._store._records["m1"] = self.store.snapshot_ciphertext()[0]
        with self.assertRaises(ValueError):
            other.get("m1")

    def test_non_json_content_is_rejected_before_persistence(self):
        item = MemoryItem("m1", object())
        with self.assertRaises(ValueError):
            self.store.put(item, key_id="memory-key")
        self.assertEqual(len(self.store), 0)

    def test_capacity_is_enforced(self):
        self.store.put(MemoryItem("m1", 1), key_id="memory-key")
        self.store.put(MemoryItem("m2", 2), key_id="memory-key")
        with self.assertRaises(MemoryError):
            self.store.put(MemoryItem("m3", 3), key_id="memory-key")


if __name__ == "__main__":
    unittest.main()
