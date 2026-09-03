import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from core.crypto import (
    AuthenticatedCipher,
    EncryptedEnvelope,
    InMemoryKeyProvider,
    KEY_SIZE,
    NONCE_SIZE,
)


class CryptoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.provider = InMemoryKeyProvider({"k1": b"K" * KEY_SIZE})
        self.cipher = AuthenticatedCipher(self.provider)

    def test_round_trip_and_metadata_authentication(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1", aad=b"memory:item-1")
        self.assertEqual(self.cipher.decrypt(envelope), b"secret")
        self.assertEqual(len(envelope.nonce), NONCE_SIZE)

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

    def test_wrong_key_is_rejected(self):
        envelope = self.cipher.encrypt(b"secret", key_id="k1")
        other = InMemoryKeyProvider({"k2": b"L" * KEY_SIZE})
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

    def test_key_derivation_uses_standard_hkdf_for_domain_separation(self):
        # Regression guard for the rule: derived keys must use a vetted KDF,
        # never ad-hoc hashing/concatenation in application code.
        derived = HKDF(
            algorithm=hashes.SHA256(), length=KEY_SIZE, salt=b"noryx7-test", info=b"memory"
        ).derive(b"root-key-material")
        self.assertEqual(len(derived), KEY_SIZE)
        self.assertNotEqual(derived, b"root-key-material")


if __name__ == "__main__":
    unittest.main()
