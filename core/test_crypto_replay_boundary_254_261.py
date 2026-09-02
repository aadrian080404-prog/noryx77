import unittest

from .crypto import CryptoIntegrity


class CryptoReplayBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)

    def test_attack_254_replayed_envelope_is_rejected(self):
        envelope = self.crypto.sign("replay", {"value": 1}, 0, nonce="nonce-254")
        self.assertTrue(self.crypto.verify(envelope))
        self.assertFalse(self.crypto.verify(envelope))

    def test_attack_255_peek_verification_does_not_consume(self):
        envelope = self.crypto.sign("replay", {"value": 2}, 0, nonce="nonce-255")
        self.assertTrue(self.crypto.verify(envelope, consume=False))
        self.assertTrue(self.crypto.verify(envelope))
        self.assertFalse(self.crypto.verify(envelope))

    def test_attack_256_reserved_counter_allows_out_of_order_consumption(self):
        counter0 = self.crypto.next_counter("replay")
        counter1 = self.crypto.next_counter("replay")
        self.assertEqual((counter0, counter1), (0, 1))
        envelope1 = self.crypto.sign("replay", {"counter": 1}, counter1, nonce="nonce-256-1")
        envelope0 = self.crypto.sign("replay", {"counter": 0}, counter0, nonce="nonce-256-0")
        self.assertTrue(self.crypto.verify(envelope1))
        self.assertTrue(self.crypto.verify(envelope0))
        self.assertFalse(self.crypto.verify(envelope0))

    def test_attack_257_consumed_counter_cannot_be_reused_with_fresh_nonce(self):
        counter = self.crypto.next_counter("replay")
        first = self.crypto.sign("replay", {"value": 1}, counter, nonce="nonce-257-a")
        second = self.crypto.sign("replay", {"value": 2}, counter, nonce="nonce-257-b")
        self.assertTrue(self.crypto.verify(first))
        self.assertFalse(self.crypto.verify(second))

    def test_attack_258_invalid_inputs_are_rejected(self):
        for value in (True, -1, 2**64):
            with self.subTest(counter=value):
                with self.assertRaises(ValueError):
                    self.crypto.sign("replay", {}, value, nonce="nonce-258")
        with self.assertRaises(ValueError):
            self.crypto.sign("", {}, 0, nonce="nonce-258")
        with self.assertRaises(ValueError):
            self.crypto.sign("replay", {}, 0, nonce=" ")

    def test_attack_259_next_counter_is_monotonic_after_verified_higher_counter(self):
        envelope = self.crypto.sign("replay", {"value": 1}, 7, nonce="nonce-259")
        self.assertTrue(self.crypto.verify(envelope))
        self.assertEqual(self.crypto.next_counter("replay"), 8)

    def test_attack_260_invalid_envelope_fields_fail_closed(self):
        canonical = self.crypto.sign("replay", {"value": 1}, 0, nonce="nonce-260")
        cases = [
            {"algorithm": "FORGED"},
            {"version": 999},
            {"domain": ""},
            {"nonce": ""},
            {"counter": True},
            {"payload": "not-bytes"},
            {"tag": "short"},
        ]
        for changes in cases:
            envelope = canonical
            for field, value in changes.items():
                object.__setattr__(envelope, field, value)
            with self.subTest(changes=changes):
                self.assertFalse(self.crypto.verify(envelope, consume=False))

    def test_attack_261_consume_false_does_not_change_counter_reservation(self):
        counter0 = self.crypto.next_counter("replay")
        counter1 = self.crypto.next_counter("replay")
        envelope0 = self.crypto.sign("replay", {"counter": 0}, counter0, nonce="nonce-261-0")
        self.assertTrue(self.crypto.verify(envelope0, consume=False))
        envelope1 = self.crypto.sign("replay", {"counter": 1}, counter1, nonce="nonce-261-1")
        self.assertTrue(self.crypto.verify(envelope1))
        self.assertTrue(self.crypto.verify(envelope0))


if __name__ == "__main__":
    unittest.main()
