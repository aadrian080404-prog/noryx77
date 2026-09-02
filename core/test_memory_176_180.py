import unittest

from .memory import MemoryItem, MemoryStore


class FailingCrypto:
    def digest(self, domain, payload):
        raise RuntimeError("crypto_failure")

    def verify_digest(self, domain, payload, digest):
        return False


class Memory176To180Tests(unittest.TestCase):
    def test_attack176_crypto_failure_does_not_insert_memory(self):
        store = MemoryStore(crypto=FailingCrypto())
        with self.assertRaises(RuntimeError):
            store.put(MemoryItem("m1", "payload"))
        self.assertEqual(len(store), 0)

    def test_attack177_crypto_failure_does_not_consume_capacity(self):
        store = MemoryStore(max_items=1, crypto=FailingCrypto())
        with self.assertRaises(RuntimeError):
            store.put(MemoryItem("m1", "payload"))
        self.assertEqual(len(store), 0)

    def test_attack178_non_canonical_content_does_not_leave_partial_state(self):
        store = MemoryStore(max_items=1)
        with self.assertRaises(TypeError):
            store.put(MemoryItem("m1", {"bad": float("nan")}))
        self.assertEqual(len(store), 0)
        self.assertEqual(store.list(), ())

    def test_attack179_failed_replacement_preserves_existing_authenticated_item(self):
        store = MemoryStore(max_items=1)
        store.put(MemoryItem("m1", "good"))
        with self.assertRaises(TypeError):
            store.put(MemoryItem("m1", {"bad": float("nan")}))
        self.assertEqual(store.get("m1").content, "good")
        self.assertEqual(len(store), 1)

    def test_attack180_successful_write_remains_authenticated(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", "good"))
        self.assertEqual(store.get("m1").content, "good")
        self.assertEqual(len(store.list()), 1)


if __name__ == "__main__":
    unittest.main()
