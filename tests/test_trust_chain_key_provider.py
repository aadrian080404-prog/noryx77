from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.device import DeviceIdentity, DeviceRole, DeviceTrust
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.trust_chain import TrustChain


class TestOnlyKeyProvider:
    def __init__(self, key):
        self._key = key

    def public_key(self, key_id):
        return self._key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def sign(self, key_id, message):
        return self._key.sign(message)


def _setup():
    agent, private = AgentIdentityAuthority.generate("kms-backed-agent")
    peer, _ = AgentIdentityAuthority.generate("peer-agent")
    attestation = AgentIdentityAuthority.sign(agent, private, b"boot:provider-test")
    device = DeviceIdentity("device-provider", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    registry = IdentityRegistry()
    registry.register(agent)
    registry.register(peer)
    return agent, private, peer, attestation, device, registry


def test_trust_chain_signs_and_verifies_without_exporting_private_key():
    agent, private, peer, attestation, device, registry = _setup()
    provider = TestOnlyKeyProvider(private)
    evidence = TrustChain.sign_with_provider(
        agent, provider, "kms://agent/key-7", device, attestation,
        session_id="provider-session", peer=peer, direction="send",
        epoch=3, action_digest=b"z" * 32,
    )
    assert TrustChain(registry).verify(
        evidence, attestation=attestation, expected_device=device,
        expected_peer=peer, session_id="provider-session", direction="send",
        expected_epoch=3, consume_replay=False,
    )


def test_trust_chain_external_provider_cannot_sign_for_another_identity():
    agent, _private, peer, attestation, device, _registry = _setup()
    wrong_provider = TestOnlyKeyProvider(Ed25519PrivateKey.generate())
    try:
        TrustChain.sign_with_provider(
            agent, wrong_provider, "kms://wrong/key", device, attestation,
            session_id="provider-session", peer=peer, direction="send",
            epoch=3, action_digest=b"z" * 32,
        )
    except PermissionError as exc:
        assert str(exc) == "signing_key_identity_mismatch"
    else:
        raise AssertionError("provider key mismatch must be rejected")


def test_trust_chain_provider_path_keeps_device_and_digest_gates():
    agent, private, peer, attestation, device, _registry = _setup()
    provider = TestOnlyKeyProvider(private)
    try:
        TrustChain.sign_with_provider(
            agent, provider, "kms://agent/key-7", device, attestation,
            session_id="provider-session", peer=peer, direction="send",
            epoch=3, action_digest=b"bad",
        )
    except ValueError as exc:
        assert str(exc) == "invalid_action_digest"
    else:
        raise AssertionError("invalid action digest must be rejected")
