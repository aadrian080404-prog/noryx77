import unittest
from dataclasses import replace
from .crypto import InMemoryKeyProvider, KEY_SIZE, KeyProvider
from .identity import AgentIdentityAuthority, IdentityRegistry
from .secure_channel import MAX_FRAME_SIZE, MAX_SEQUENCE, SecureChannel


class SecureChannelTests(unittest.TestCase):
    def setUp(self):
        self.provider = InMemoryKeyProvider({"channel": b"k" * KEY_SIZE})
        self.sender = SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send")
        self.receiver = SecureChannel(self.provider, key_id="channel", local_id="agent-b", peer_id="agent-a", session_id="session-1", direction="send")

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
        with self.assertRaisesRegex(ValueError, "channel_identity_mismatch"):
            self.receiver.receive(replace(frame, sender_id="agent-c"))

    def test_session_substitution_is_rejected(self):
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "channel_identity_mismatch"):
            self.receiver.receive(replace(frame, session_id="session-2"))

    def test_payload_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            self.receiver.receive(replace(frame, payload=b"hullo"))

    def test_mac_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            self.receiver.receive(replace(frame, mac=b"x" * len(frame.mac)))

    def test_version_tampering_is_rejected(self):
        frame = self.sender.send(b"hello")
        with self.assertRaisesRegex(ValueError, "invalid_secure_frame"):
            self.receiver.receive(replace(frame, version=2))

    def test_wrong_key_is_rejected(self):
        other = InMemoryKeyProvider({"other": b"z" * KEY_SIZE})
        receiver = SecureChannel(other, key_id="other", local_id="agent-b", peer_id="agent-a", session_id="session-1", direction="send")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            receiver.receive(self.sender.send(b"hello"))

    def test_provider_failure_fails_closed(self):
        class BrokenProvider(KeyProvider):
            def get_key(self, key_id):
                raise RuntimeError("provider unavailable")
        channel = SecureChannel(BrokenProvider(), key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send")
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
        receive_side = SecureChannel(self.provider, key_id="channel", local_id="agent-b", peer_id="agent-a", session_id="session-1", direction="receive")
        with self.assertRaisesRegex(ValueError, "frame_authentication_failed"):
            receive_side.receive(self.sender.send(b"hello"))

    def test_constructor_rejects_same_identity(self):
        with self.assertRaisesRegex(ValueError, "local_and_peer_id_must_differ"):
            SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-a", session_id="session-1", direction="send")

    def _trusted_channels(self):
        local, _ = AgentIdentityAuthority.generate("agent-a")
        peer, _ = AgentIdentityAuthority.generate("agent-b")
        registry = IdentityRegistry()
        registry.register(local)
        registry.register(peer)
        sender = SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send", identity_registry=registry, local_identity=local, peer_identity=peer)
        receiver = SecureChannel(self.provider, key_id="channel", local_id="agent-b", peer_id="agent-a", session_id="session-1", direction="send", identity_registry=registry, local_identity=peer, peer_identity=local)
        return registry, local, peer, sender, receiver

    def test_trusted_identities_enable_channel(self):
        _, _, _, sender, receiver = self._trusted_channels()
        self.assertEqual(receiver.receive(sender.send(b"trusted")), b"trusted")

    def test_channel_rejects_untrusted_peer_identity(self):
        local, _ = AgentIdentityAuthority.generate("agent-a")
        peer, _ = AgentIdentityAuthority.generate("agent-b")
        registry = IdentityRegistry()
        registry.register(local)
        with self.assertRaisesRegex(ValueError, "channel_identity_untrusted"):
            SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send", identity_registry=registry, local_identity=local, peer_identity=peer)

    def test_channel_rejects_identity_id_substitution(self):
        local, _ = AgentIdentityAuthority.generate("agent-a")
        peer, _ = AgentIdentityAuthority.generate("agent-b")
        forged_peer, _ = AgentIdentityAuthority.generate("agent-c")
        registry = IdentityRegistry()
        registry.register(local)
        registry.register(peer)
        registry.register(forged_peer)
        with self.assertRaisesRegex(ValueError, "channel_identity_mismatch"):
            SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send", identity_registry=registry, local_identity=local, peer_identity=forged_peer)

    def test_revocation_blocks_channel_construction(self):
        local, _ = AgentIdentityAuthority.generate("agent-a")
        peer, _ = AgentIdentityAuthority.generate("agent-b")
        registry = IdentityRegistry()
        registry.register(local)
        registry.register(peer)
        registry.revoke("agent-b")
        with self.assertRaisesRegex(ValueError, "channel_identity_untrusted"):
            SecureChannel(self.provider, key_id="channel", local_id="agent-a", peer_id="agent-b", session_id="session-1", direction="send", identity_registry=registry, local_identity=local, peer_identity=peer)

    def test_revocation_blocks_existing_channel_send_and_receive(self):
        registry, _, _, sender, receiver = self._trusted_channels()
        frame = sender.send(b"before-revocation")
        registry.revoke("agent-b")
        with self.assertRaisesRegex(ValueError, "channel_identity_untrusted"):
            sender.send(b"after-revocation")
        with self.assertRaisesRegex(ValueError, "channel_identity_untrusted"):
            receiver.receive(frame)


if __name__ == "__main__":
    unittest.main()
