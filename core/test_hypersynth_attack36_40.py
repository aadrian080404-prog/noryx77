import unittest

from .audit import AuditLog
from .crypto import CryptoEnvelope, CryptoIntegrity


class Attack36To40Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)

    def test_attack36_algorithm_downgrade_is_rejected(self):
        envelope = self.crypto.sign("task", {"id": "t36"}, 0, nonce="n36")
        forged = CryptoEnvelope(envelope.domain, envelope.nonce, envelope.counter, envelope.payload, envelope.tag, "SHA1", envelope.version)
        self.assertFalse(self.crypto.verify(forged))

    def test_attack37_version_confusion_is_rejected(self):
        envelope = self.crypto.sign("task", {"id": "t37"}, 0, nonce="n37")
        forged = CryptoEnvelope(envelope.domain, envelope.nonce, envelope.counter, envelope.payload, envelope.tag, envelope.algorithm, 2)
        self.assertFalse(self.crypto.verify(forged))

    def test_attack38_oversized_identity_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            self.crypto.sign("d" * 129, {}, 0)
        with self.assertRaises(ValueError):
            self.crypto.sign("task", {}, 0, nonce="n" * 257)

    def test_attack39_counter_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            self.crypto.sign("task", {}, 2**64)

    def test_attack40_audit_authentication_field_cannot_be_injected(self):
        audit = AuditLog(b"k" * 32)
        with self.assertRaisesRegex(ValueError, "audit reserved field"):
            audit.record("event", auth="forged")


if __name__ == "__main__":
    unittest.main()
