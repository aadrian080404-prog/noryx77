"""Unified fail-closed trust chain for NORYX7 privileged execution.

This module composes existing primitives instead of replacing them. It binds
agent identity, device identity/trust, attestation, Secure Channel context,
execution epoch and action digest into one signed evidence object. Personality
metadata is deliberately absent: cognition can never grant trust.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .authorization_replay import AuthorizationReplayGuard
from .device import DeviceCapabilityGate, DeviceIdentity, DeviceTrust
from .identity import AgentAttestation, AgentIdentity, AgentIdentityAuthority, IdentityRegistry

VERSION: Final[int] = 1
MAX_TEXT: Final[int] = 1024
MAX_ACTION_DIGEST_SIZE: Final[int] = 32
_DOMAIN: Final[bytes] = b"noryx7/trust-chain/v1/"
_CHANNEL_DOMAIN: Final[bytes] = b"noryx7/secure-channel/identity-binding/v1/"


def _field(value: str, name: str) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{name}")
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_TEXT:
        raise ValueError(f"{name}_size_exceeded")
    return len(encoded).to_bytes(4, "big") + encoded


def channel_binding_digest(local: AgentIdentity, peer: AgentIdentity, session_id: str, direction: str) -> bytes:
    """Canonical digest matching the Secure Channel identity/session contract."""
    if not isinstance(local, AgentIdentity) or not isinstance(peer, AgentIdentity):
        raise ValueError("channel_identities_required")
    if not local.is_well_formed() or not peer.is_well_formed():
        raise ValueError("invalid_channel_identity")
    if local.agent_id == peer.agent_id:
        raise ValueError("channel_identities_must_differ")
    if direction not in {"send", "receive"}:
        raise ValueError("invalid_direction")
    local_fp = sha256(_CHANNEL_DOMAIN + local.version.to_bytes(2, "big") + _field(local.agent_id, "agent_id") + local.public_key).digest()
    peer_fp = sha256(_CHANNEL_DOMAIN + peer.version.to_bytes(2, "big") + _field(peer.agent_id, "agent_id") + peer.public_key).digest()
    pair = b"".join(sorted((local_fp, peer_fp)))
    return sha256(_CHANNEL_DOMAIN + pair + _field(session_id, "session_id") + _field(direction, "direction")).digest()


def _evidence_message(agent: AgentIdentity, device: DeviceIdentity, attestation_digest: bytes,
                      channel_digest: bytes, epoch: int, action_digest: bytes) -> bytes:
    if not agent.is_well_formed():
        raise ValueError("invalid_agent_identity")
    if not isinstance(device, DeviceIdentity):
        raise ValueError("invalid_device_identity")
    if device.trust is not DeviceTrust.VERIFIED:
        raise PermissionError("device_not_verified")
    if not isinstance(attestation_digest, bytes) or len(attestation_digest) != 32:
        raise ValueError("invalid_attestation_digest")
    if not isinstance(channel_digest, bytes) or len(channel_digest) != 32:
        raise ValueError("invalid_channel_digest")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError("invalid_epoch")
    if not isinstance(action_digest, bytes) or len(action_digest) != MAX_ACTION_DIGEST_SIZE:
        raise ValueError("invalid_action_digest")
    return (
        _DOMAIN + VERSION.to_bytes(2, "big")
        + _field(agent.agent_id, "agent_id") + agent.public_key
        + _field(device.device_id, "device_id") + _field(device.platform, "platform")
        + device.role.value.encode("ascii") + b"\x00"
        + attestation_digest + channel_digest
        + epoch.to_bytes(8, "big") + action_digest
    )


@dataclass(frozen=True)
class TrustEvidence:
    agent: AgentIdentity
    device: DeviceIdentity
    attestation_digest: bytes
    channel_digest: bytes
    epoch: int
    action_digest: bytes
    signature: bytes


class TrustChain:
    """Verifies identity, attestation, channel, live device capability and replay state."""

    def __init__(self, registry: IdentityRegistry, replay_guard: AuthorizationReplayGuard | None = None) -> None:
        if not isinstance(registry, IdentityRegistry):
            raise ValueError("identity_registry_required")
        self.registry = registry
        self.replay_guard = replay_guard or AuthorizationReplayGuard()

    @staticmethod
    def attest_digest(attestation: AgentAttestation) -> bytes:
        if not isinstance(attestation, AgentAttestation) or not attestation.is_well_formed():
            raise ValueError("invalid_attestation")
        return sha256(attestation.statement + attestation.signature).digest()

    @staticmethod
    def sign(agent: AgentIdentity, private_key: Ed25519PrivateKey, device: DeviceIdentity,
             attestation: AgentAttestation, *, session_id: str, peer: AgentIdentity,
             direction: str, epoch: int, action_digest: bytes) -> TrustEvidence:
        if agent.agent_id != attestation.identity.agent_id or agent.public_key != attestation.identity.public_key:
            raise ValueError("attestation_identity_mismatch")
        if not AgentIdentityAuthority.verify(attestation):
            raise ValueError("attestation_invalid")
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("identity_private_key_required")
        raw_public = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if not compare_digest(raw_public, agent.public_key):
            raise ValueError("identity_private_key_mismatch")
        channel_digest = channel_binding_digest(agent, peer, session_id, direction)
        attestation_digest = TrustChain.attest_digest(attestation)
        message = _evidence_message(agent, device, attestation_digest, channel_digest, epoch, action_digest)
        return TrustEvidence(agent, device, attestation_digest, channel_digest, epoch, bytes(action_digest), private_key.sign(message))

    def verify(self, evidence: TrustEvidence, *, attestation: AgentAttestation,
               expected_device: DeviceIdentity, expected_peer: AgentIdentity,
               session_id: str, direction: str, expected_epoch: int,
               consume_replay: bool = True) -> bool:
        if not isinstance(evidence, TrustEvidence) or not isinstance(attestation, AgentAttestation):
            return False
        if evidence.device != expected_device or evidence.agent != attestation.identity:
            return False
        if expected_device.trust is not DeviceTrust.VERIFIED:
            return False
        if evidence.epoch != expected_epoch:
            return False
        try:
            if not self.registry.is_trusted(evidence.agent):
                return False
            if not AgentIdentityAuthority.verify(attestation, self.registry):
                return False
            if not compare_digest(evidence.attestation_digest, self.attest_digest(attestation)):
                return False
            expected_channel = channel_binding_digest(evidence.agent, expected_peer, session_id, direction)
            if not compare_digest(evidence.channel_digest, expected_channel):
                return False
            message = _evidence_message(evidence.agent, evidence.device, evidence.attestation_digest,
                                        evidence.channel_digest, evidence.epoch, evidence.action_digest)
            Ed25519PublicKey.from_public_bytes(evidence.agent.public_key).verify(evidence.signature, message)
            if consume_replay and not self.replay_guard.consume(evidence.action_digest):
                return False
            return True
        except (InvalidSignature, ValueError, TypeError, PermissionError):
            return False

    def verify_live_device_capability(
        self,
        evidence: TrustEvidence,
        *,
        device_gate: DeviceCapabilityGate,
        capability: str,
        now: int,
        expected_epoch: int,
    ) -> bool:
        """Require the live device gate to authorize the exact trust-chain action.

        This closes a time-of-check/time-of-use gap: a previously verified
        DeviceIdentity snapshot is insufficient after capability revocation,
        expiry, epoch rotation, isolation, or device replacement.
        """
        if not isinstance(evidence, TrustEvidence) or not isinstance(device_gate, DeviceCapabilityGate):
            return False
        if evidence.device != device_gate.identity:
            return False
        if evidence.epoch != expected_epoch:
            return False
        if not isinstance(capability, str) or not capability.strip():
            return False
        if isinstance(now, bool) or not isinstance(now, int) or now < 0:
            return False
        return device_gate.allows(capability, now=now, epoch=expected_epoch)
