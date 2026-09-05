"""Cryptographic binding of personality metadata to an agent execution epoch.

The binding is integrity/context metadata only. It never grants capabilities,
changes authorization, or changes the security/recovery policy.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .identity import AgentIdentity, IdentityRegistry
from .personality import PersonalityProfile

MAX_ID_BYTES = 256
MAX_KEY_BYTES = 256
SIGNATURE_SIZE = 64
_DOMAIN = b"noryx7/personality-binding/v2/"


def _bounded_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ValueError(f"invalid_{name}")
    return value


def _canonical(agent_id: str, personality_fingerprint: str, epoch: int) -> bytes:
    _bounded_text(agent_id, "agent_id")
    _bounded_text(personality_fingerprint, "personality_fingerprint")
    if len(personality_fingerprint) != 64:
        raise ValueError("invalid_personality_fingerprint")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError("invalid_epoch")
    return _DOMAIN + agent_id.encode("utf-8") + b"|" + personality_fingerprint.encode("ascii") + b"|" + epoch.to_bytes(8, "big")


def bind_personality(profile: PersonalityProfile, *, agent_id: str, epoch: int, key: bytes) -> str:
    if not isinstance(profile, PersonalityProfile):
        raise TypeError("profile_must_be_PersonalityProfile")
    if profile.agent_id != agent_id:
        raise ValueError("agent_identity_mismatch")
    if not isinstance(key, bytes) or not 16 <= len(key) <= MAX_KEY_BYTES:
        raise ValueError("invalid_binding_key")
    return hmac.new(key, _canonical(agent_id, profile.fingerprint, epoch), hashlib.sha256).hexdigest()


def verify_personality_binding(profile: PersonalityProfile, *, agent_id: str, epoch: int, binding: str, key: bytes) -> bool:
    if not isinstance(binding, str) or len(binding) != 64:
        return False
    try:
        expected = bind_personality(profile, agent_id=agent_id, epoch=epoch, key=key)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(expected, binding)


@dataclass(frozen=True)
class SignedPersonalityBinding:
    identity: AgentIdentity
    personality_fingerprint: str
    epoch: int
    signature: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.identity, AgentIdentity) or not self.identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        if not isinstance(self.personality_fingerprint, str) or len(self.personality_fingerprint) != 64:
            raise ValueError("invalid_personality_fingerprint")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("invalid_epoch")
        if not isinstance(self.signature, bytes) or len(self.signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_signature")


def _signed_message(identity: AgentIdentity, personality_fingerprint: str, epoch: int) -> bytes:
    return _canonical(identity.agent_id, personality_fingerprint, epoch) + identity.public_key


def sign_identity_personality_binding(
    profile: PersonalityProfile,
    *,
    identity: AgentIdentity,
    private_key: Ed25519PrivateKey,
    epoch: int,
) -> SignedPersonalityBinding:
    if profile.agent_id != identity.agent_id:
        raise ValueError("agent_identity_mismatch")
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key_must_be_ed25519")
    raw_public = private_key.public_key().public_bytes_raw()
    if raw_public != identity.public_key:
        raise ValueError("identity_private_key_mismatch")
    message = _signed_message(identity, profile.fingerprint, epoch)
    return SignedPersonalityBinding(identity, profile.fingerprint, epoch, private_key.sign(message))


def verify_identity_personality_binding(
    binding: SignedPersonalityBinding,
    *,
    profile: PersonalityProfile,
    registry: IdentityRegistry | None = None,
    expected_epoch: int | None = None,
) -> bool:
    if not isinstance(binding, SignedPersonalityBinding) or not isinstance(profile, PersonalityProfile):
        return False
    if profile.agent_id != binding.identity.agent_id or profile.fingerprint != binding.personality_fingerprint:
        return False
    if expected_epoch is not None and binding.epoch != expected_epoch:
        return False
    if registry is not None and not registry.is_trusted(binding.identity):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(binding.identity.public_key).verify(
            binding.signature,
            _signed_message(binding.identity, binding.personality_fingerprint, binding.epoch),
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
