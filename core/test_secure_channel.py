import unittest

from dataclasses import replace

from .crypto import InMemoryKeyProvider, KEY_SIZE, KeyProvider
from .secure_channel import MAX_FRAME_SIZE, MAX_SEQUENCE, SecureChannel


class SecureChannelTests(unittest.TestCase):
    def setUp(self):
        self.provider = InMemoryKeyProvider({"channel": b"k" * KEY_SIZE})
        self.sender = SecureChannel(
            self.provider,
            key_id="channel",
            local_id="agent-a",
            peer_id="agent-b",
            session_id="session-1",
            direction="send",
        )
        self.receiver = SecureChannel(
            self.provider,
            key_id="channel",
            local_id="agent-b",
            peer_id="agent-a",
            session_id="session-1",
            direction="send",
        )

    def test_round_trip(self):
        frame = self.sender.send(b"hello")
        self.assertEqual(self.receiver.receive(frame), b"hello")

    def test_replay_is_rejected(self):
        frame = self.sender.send(b"hello")
        self.receiver.receive(frame)
        with self.assertRaisesRegex(ValueError, "replayed_frame"):
            self.receiver.receive(frame)

    def test_sequence_rollback_is_rejected(self):
        first = self.sender.send(b"one")
        second = self.sender.send(b"two")
        self.receiver.receive(second)
        with self.assertRaisesRegex(ValueError, "replayed_frame"):
            self.receiver.receive(first)

    def test_sender_identity_substitution_is_rejected(self):
        frame = self.sender.send(b"hello")
        forged = replace(frame, sender_id="agent-c")
        with self.assertRaisesRegex(ValueError, "channel_identity_mismatch"):
            self.receiver.receive(forged)

    def test_session_substitution_is_rejected(self):
        frame = self.sender.send(b"hello")
        forged = replace(frame, session_id="session-2")
        with self.assertRaisesRegex(ValueError, "channel_identity_mismatch"):
            self.receiver.receive(forged)

    def test_payload_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        forged = replace(frame, payload=b"hullo")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            self.receiver.receive(forged)

    def test_mac_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        forged = replace(frame, mac=b"x" * len(frame.mac))
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            self.receiver.receive(forged)

    def test_version_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        forged = replace(frame, version=2)
        with self.assertRaisesRegex(ValueError, "invalid_secure_frame"):
            self.receiver.receive(forged)

    def test_wrong_key_is_rejected(self):
        other = InMemoryKeyProvider({"other": b"z" * KEY_SIZE})
        receiver = SecureChannel(
            other,
            key_id="other",
            local_id="agent-b",
            peer_id="agent-a",
            session_id="session-1",
            direction="send",
        )
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            receiver.receive(frame)

    def test_provider_failure_fails_closed(self):
        class BrokenProvider(KeyProvider):
            def get_key(self, key_id):
                raise RuntimeError("provider unavailable")

        channel = SecureChannel(
            BrokenProvider(),
            key_id="channel",
            local_id="agent-a",
            peer_id="agent-b",
            session_id="session-1",
            direction="send",
        )
        with self.assertRaisesRegex(ValueError, "channel_key_unavailable"):
            channel.send(b"hello")

    def test_oversized_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "frame_size_exceeded"):
            self.sender.send(b"x" * (MAX_FRAME_SIZE + 1))

    def test_malformed_frame_is_rejected(self):
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "invalid_secure_frame"):
            self.receiver.receive(replace(frame, sequence=True))

    def test_sequence_exhaustion_is_rejected(self):
        self.sender._send_sequence = MAX_SEQUENCE + 1
        with self.assertRaisesRegex(ValueError, "sequence_exhausted"):
            self.sender.send(b"hello")

    def test_directional_keys_do_not_reflect(self):
        receive_side = SecureChannel(
            self.provider,
            key_id="channel",
            local_id="agent-b",
            peer_id="agent-a",
            session_id="session-1",
            direction="receive",
        )
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            receive_side.receive(frame)

    def test_constructor_rejects_same_identity(self):
        with self.assertRaisesRegex(ValueError, "local_and_peer_id_must_differ"):
            SecureChannel(
                self.provider,
                key_id="channel",
                local_id="agent-a",
                peer_id="agent-a",
                session_id="session-1",
                direction="send",
            )


if __name__ == "__main__":
    unittest.main()
