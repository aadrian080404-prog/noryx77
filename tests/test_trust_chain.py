from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authorization_replay import AuthorizationReplayGuard
from core.device import CapabilityGrant, DeviceCapabilityGate, DeviceIdentity, DeviceRole, DeviceTrust
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.trust_chain import TrustChain, channel_binding_digest


def _fixture():
    agent, private = AgentIdentityAuthority.generate("agent-a")
    peer, _ = AgentIdentityAuthority.generate("agent-b")
    registry = IdentityRegistry()
    registry.register(agent)
    registry.register(peer)
    device = DeviceIdentity("device-a", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    attestation = AgentIdentityAuthority.sign(agent, private, b"boot:v1:device-a")
    digest = b"a" * 32
    return agent, private, peer, registry, device, attestation, digest


def _evidence():
    agent, private, peer, registry, device, attestation, digest = _fixture()
    evidence = TrustChain.sign(
        agent, private, device, attestation,
        session_id="session-1", peer=peer, direction="send", epoch=7,
        action_digest=digest,
    )
    return evidence, agent, private, peer, registry, device, attestation, digest


def test_valid_chain_is_accepted_once():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    guard = AuthorizationReplayGuard()
    chain = TrustChain(registry, guard)
    assert chain.verify(evidence, attestation=attestation, expected_device=device,
                        expected_peer=peer, session_id="session-1", direction="send",
                        expected_epoch=7)
    assert not chain.verify(evidence, attestation=attestation, expected_device=device,
                            expected_peer=peer, session_id="session-1", direction="send",
                            expected_epoch=7)


def test_identity_swap_is_rejected():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    other, other_private = AgentIdentityAuthority.generate("agent-c")
    forged = replace(evidence, agent=other)
    assert not TrustChain(registry).verify(forged, attestation=attestation, expected_device=device,
                                           expected_peer=peer, session_id="session-1",
                                           direction="send", expected_epoch=7)
    assert other_private is not None


def test_device_swap_is_rejected():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    other_device = DeviceIdentity("device-b", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    assert not TrustChain(registry).verify(evidence, attestation=attestation, expected_device=other_device,
                                           expected_peer=peer, session_id="session-1",
                                           direction="send", expected_epoch=7)


def test_attestation_tamper_is_rejected():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    forged_attestation = replace(attestation, statement=b"boot:forged")
    assert not TrustChain(registry).verify(evidence, attestation=forged_attestation,
                                           expected_device=device, expected_peer=peer,
                                           session_id="session-1", direction="send", expected_epoch=7)


def test_epoch_and_channel_context_swaps_are_rejected():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    chain = TrustChain(registry)
    assert not chain.verify(evidence, attestation=attestation, expected_device=device,
                            expected_peer=peer, session_id="session-1", direction="send", expected_epoch=8)
    assert not chain.verify(evidence, attestation=attestation, expected_device=device,
                            expected_peer=peer, session_id="session-2", direction="send", expected_epoch=7)
    assert not chain.verify(evidence, attestation=attestation, expected_device=device,
                            expected_peer=peer, session_id="session-1", direction="receive", expected_epoch=7)


def test_revoked_identity_is_rejected():
    evidence, agent, private, peer, registry, device, attestation, digest = _evidence()
    registry.revoke(agent.agent_id)
    assert not TrustChain(registry).verify(evidence, attestation=attestation, expected_device=device,
                                           expected_peer=peer, session_id="session-1",
                                           direction="send", expected_epoch=7)


def test_unverified_device_is_rejected_before_execution():
    agent, private, peer, registry, _, attestation, digest = _fixture()
    device = DeviceIdentity("device-a", "android", DeviceRole.CLIENT, DeviceTrust.UNKNOWN)
    try:
        TrustChain.sign(agent, private, device, attestation, session_id="session-1",
                        peer=peer, direction="send", epoch=7, action_digest=digest)
    except PermissionError:
        pass
    else:
        raise AssertionError("unverified device must fail closed")


def test_invalid_action_digest_and_key_swap_fail_closed():
    agent, private, peer, registry, device, attestation, digest = _fixture()
    try:
        TrustChain.sign(agent, private, device, attestation, session_id="session-1",
                        peer=peer, direction="send", epoch=7, action_digest=b"bad")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid action digest must fail closed")

    wrong_key = Ed25519PrivateKey.generate()
    try:
        TrustChain.sign(agent, wrong_key, device, attestation, session_id="session-1",
                        peer=peer, direction="send", epoch=7, action_digest=digest)
    except ValueError:
        pass
    else:
        raise AssertionError("private-key swap must fail closed")


def test_channel_binding_is_order_independent_for_identity_pair_but_direction_bound():
    agent, _, peer, *_ = _fixture()
    a = channel_binding_digest(agent, peer, "session-1", "send")
    b = channel_binding_digest(peer, agent, "session-1", "send")
    c = channel_binding_digest(agent, peer, "session-1", "receive")
    assert a == b
    assert a != c


def test_live_device_capability_is_required_for_execution_context():
    evidence, _, _, _, _, device, _, _ = _evidence()
    gate = DeviceCapabilityGate(device)
    gate.grant(CapabilityGrant("transfer", device.device_id, expires_at=100, epoch=7))
    chain = TrustChain(IdentityRegistry())

    assert chain.verify_live_device_capability(
        evidence, device_gate=gate, capability="transfer", now=50, expected_epoch=7
    )

    gate.revoke("transfer")
    assert not chain.verify_live_device_capability(
        evidence, device_gate=gate, capability="transfer", now=50, expected_epoch=7
    )


def test_live_device_epoch_and_identity_swaps_fail_closed():
    evidence, _, _, _, _, device, _, _ = _evidence()
    gate = DeviceCapabilityGate(device)
    gate.grant(CapabilityGrant("transfer", device.device_id, expires_at=100, epoch=7))
    chain = TrustChain(IdentityRegistry())

    assert not chain.verify_live_device_capability(
        evidence, device_gate=gate, capability="transfer", now=101, expected_epoch=7
    )
    assert not chain.verify_live_device_capability(
        evidence, device_gate=gate, capability="transfer", now=50, expected_epoch=8
    )
    other = DeviceCapabilityGate(DeviceIdentity("device-b", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED))
    other.grant(CapabilityGrant("transfer", "device-b", expires_at=100, epoch=7))
    assert not chain.verify_live_device_capability(
        evidence, device_gate=other, capability="transfer", now=50, expected_epoch=7
    )
