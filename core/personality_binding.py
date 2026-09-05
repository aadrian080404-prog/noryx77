"""Cryptographic binding of personality metadata to an agent execution epoch."""
from __future__ import annotations

import hashlib
import hmac

from .personality import PersonalityProfile

MAX_ID_BYTES = 256
MAX_KEY_BYTES = 256


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
    return f"noryx7/personality-binding/v1|{agent_id}|{personality_fingerprint}|{epoch}".encode("utf-8")


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
