import unittest

from core.crypto import (
    ALGORITHM,
    CRYPTO_VERSION,
    AuthenticatedCipher,
    EncryptedEnvelope,
    InMemoryKeyProvider,
    KEY_SIZE,
    MAX_PLAINTEXT_SIZE,
    NONCE_SIZE,
    derive_subkey,
)


class CryptoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.provider = InMemoryKeyProvider({"k1": b"K" * KEY_SIZE, "k2": b"L" * KEY_SIZE})
        self.cipher = AuthenticatedCipher(self.provider)

    def test_round_trip_and_metadata_authentication(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1", aad=b"memory:item-1")
        self.assertEqual(self.cipher.decrypt(envelope), b"secret")
        self.assertEqual(len(envelope.nonce), NONCE_SIZE)
        self.assertEqual(envelope.version, CRYPTO_VERSION)
        self.assertEqual(envelope.algorithm, ALGORITHM)

        tampered = EncryptedEnvelope(envelope.key_id, envelope.nonce, envelope.ciphertext, b"memory:item-2")
        with self.assertRaises(ValueError):
            self.cipher.decrypt(tampered)

    def test_ciphertext_tampering_is_rejected(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1")
        altered = bytearray(envelope.ciphertext)
        altered[-1] ^= 1
        tampered = EncryptedEnvelope(envelope.key_id, envelope.nonce, bytes(altered), envelope.aad)
        with self.assertRaises(ValueError):
            self.cipher.decrypt(tampered)

    def test_key_identity_is_authenticated(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1")
        forged = EncryptedEnvelope("k2", envelope.nonce, envelope.ciphertext, envelope.aad)
        with self.assertRaises(ValueError):
            self.cipher.decrypt(forged)

    def test_wrong_key_is_rejected(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1")
        other = InMemoryKeyProvider({"k3": b"M" * KEY_SIZE})
        with self.assertRaises(KeyError):
            AuthenticatedCipher(other).decrypt(envelope)

    def test_key_size_and_duplicate_registration_are_strict(self):
        with self.assertRaises(ValueError):
            self.provider.add("bad", b"short")
        with self.assertRaises(ValueError):
            self.provider.add("k1", b"K" * KEY_SIZE)

    def test_malformed_envelope_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cipher.decrypt(object())
        with self.assertRaises(ValueError):
            self.cipher.decrypt(EncryptedEnvelope("k1", b"x", b"not-valid"))
        envelope = self.cipher.encrypt(b"secret", key_id="k1")
        with self.assertRaises(ValueError):
            self.cipher.decrypt(EncryptedEnvelope(envelope.key_id, envelope.nonce, envelope.ciphertext, envelope.aad, 99, ALGORITHM))

    def test_plaintext_resource_limit_is_enforced(self):
        with self.assertRaises(ValueError):
            self.cipher.encrypt(b"x" * (MAX_PLAINTEXT_SIZE + 1), key_id="k1")

    def test_key_derivation_is_domain_separated(self):
        root = b"R" * KEY_SIZE
        first = derive_subkey(root, salt=b"salt", context=b"memory")
        second = derive_subkey(root, salt=b"salt", context=b"audit")
        self.assertEqual(len(first), KEY_SIZE)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            derive_subkey(b"short", salt=b"salt", context=b"memory")


if __name__ == "__main__":
    unittest.main()
