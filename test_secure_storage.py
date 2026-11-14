import unittest

from core.crypto import AuthenticatedCipher, InMemoryKeyProvider, KEY_SIZE
from core.secure_storage import EncryptedRecordStore


class EncryptedRecordStoreTests(unittest.TestCase):
    def setUp(self):
        provider = InMemoryKeyProvider({"k1": b"K" * KEY_SIZE})
        self.store = EncryptedRecordStore(
            AuthenticatedCipher(provider), namespace="memory", max_records=2
        )

    def test_round_trip_and_ciphertext_only_snapshot(self):
        self.store.put("item-1", b"top-secret", key_id="k1")
        self.assertEqual(self.store.get("item-1"), b"top-secret")
        snapshot = self.store.snapshot_ciphertext()
        self.assertEqual(len(snapshot), 1)
        self.assertNotIn(b"top-secret", snapshot[0].envelope.ciphertext)

    def test_record_identity_is_authenticated(self):
        self.store.put("item-1", b"top-secret", key_id="k1")
        original = self.store._records["item-1"]
        self.store._records["item-2"] = type(original)("item-2", original.envelope)
        with self.assertRaises(ValueError):
            self.store.get("item-2")

    def test_missing_and_invalid_records_fail_closed(self):
        self.assertIsNone(self.store.get("missing"))
        self.assertIsNone(self.store.get(""))
        with self.assertRaises(ValueError):
            self.store.put("", b"x", key_id="k1")

    def test_capacity_is_enforced(self):
        self.store.put("one", b"1", key_id="k1")
        self.store.put("two", b"2", key_id="k1")
        with self.assertRaises(MemoryError):
            self.store.put("three", b"3", key_id="k1")

    def test_ciphertext_tampering_is_detected(self):
        self.store.put("item-1", b"top-secret", key_id="k1")
        stored = self.store._records["item-1"]
        altered = bytearray(stored.envelope.ciphertext)
        altered[-1] ^= 1
        tampered = type(stored.envelope)(
            stored.envelope.key_id,
            stored.envelope.nonce,
            bytes(altered),
            stored.envelope.aad,
        )
        self.store._records["item-1"] = type(stored)("item-1", tampered)
        with self.assertRaises(ValueError):
            self.store.get("item-1")


if __name__ == "__main__":
    unittest.main()
