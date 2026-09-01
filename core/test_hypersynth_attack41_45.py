import unittest

from .crypto import CryptoEnvelope, CryptoIntegrity
from .crypto_policy import CryptoPolicy


class Attack41To45Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)
        self.policy = CryptoPolicy(self.crypto)

    def test_attack41_non_json_object_is_rejected(self):
        class Unstable:
            def __str__(self):
                return "same"
        with self.assertRaises(TypeError):
            self.policy.canonical(Unstable())

    def test_attack42_non_finite_float_is_rejected(self):
        with self.assertRaises(TypeError):
            self.policy.canonical(float("nan"))
        with self.assertRaises(TypeError):
            self.policy.canonical(float("inf"))

    def test_attack43_payload_size_is_bounded(self):
        self.policy.MAX_PAYLOAD_BYTES = 16
        with self.assertRaisesRegex(ValueError, "crypto_payload_too_large"):
            self.policy.canonical({"payload": "x" * 100})

    def test_attack44_envelope_metadata_is_bound_to_algorithm_and_version(self):
        envelope = self.crypto.sign("task", {"id": "t44"}, 0, nonce="n44")
        wrong_algorithm = CryptoEnvelope(envelope.domain, envelope.nonce, envelope.counter, envelope.payload, envelope.tag, "OTHER", envelope.version)
        wrong_version = CryptoEnvelope(envelope.domain, envelope.nonce, envelope.counter, envelope.payload, envelope.tag, envelope.algorithm, 99)
        self.assertFalse(self.policy.verify_envelope(wrong_algorithm))
        self.assertFalse(self.policy.verify_envelope(wrong_version))
        self.assertTrue(self.policy.verify_envelope(envelope))

    def test_attack45_non_consuming_verification_does_not_create_replay_state(self):
        envelope = self.crypto.sign("task", {"id": "t45"}, 0, nonce="n45")
        self.assertTrue(self.policy.verify_envelope(envelope, consume=False))
        self.assertTrue(self.policy.verify_envelope(envelope, consume=False))
        self.assertTrue(self.policy.verify_envelope(envelope))
        self.assertFalse(self.policy.verify_envelope(envelope))


if __name__ == "__main__":
    unittest.main()
