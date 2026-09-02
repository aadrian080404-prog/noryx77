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

    def _tampered(self, **changes):
        envelope = self.crypto.sign("test", {"value": 4}, 1, nonce="nonce-tamper")
        for field, value in changes.items():
            object.__setattr__(envelope, field, value)
        return envelope

    def test_attack_248_payload_tampering_is_detected(self):
        self.assertFalse(self.crypto.verify(self._tampered(payload=b'{"value":999}'), consume=False))

    def test_attack_249_tag_tampering_is_detected(self):
        envelope = self.crypto.sign("test", {"value": 5}, 1, nonce="nonce-tag")
        object.__setattr__(envelope, "tag", "0" * 64)
        self.assertFalse(self.crypto.verify(envelope, consume=False))

    def test_attack_250_domain_tampering_is_detected(self):
        self.assertFalse(self.crypto.verify(self._tampered(domain="other"), consume=False))

    def test_attack_251_nonce_tampering_is_detected(self):
        self.assertFalse(self.crypto.verify(self._tampered(nonce="nonce-forged"), consume=False))

    def test_attack_252_counter_tampering_is_detected(self):
        self.assertFalse(self.crypto.verify(self._tampered(counter=2), consume=False))

    def test_attack_253_algorithm_and_version_tampering_is_rejected(self):
        envelope = self.crypto.sign("test", {"value": 6}, 1, nonce="nonce-meta")
        object.__setattr__(envelope, "algorithm", "FORGED")
        self.assertFalse(self.crypto.verify(envelope, consume=False))
        object.__setattr__(envelope, "algorithm", self.crypto.ALGORITHM)
        object.__setattr__(envelope, "version", 999)
        self.assertFalse(self.crypto.verify(envelope, consume=False))


if __name__ == "__main__":
    unittest.main()
