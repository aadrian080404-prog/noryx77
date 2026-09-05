"""Bounded interaction context for routing user-understanding signals.

This module is deliberately an orchestration boundary: it accepts only an
already-derived UserUnderstandingProfile and exposes a compact, deterministic
context. Raw user content never crosses this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from .user_understanding import UserSignal, UserUnderstandingProfile

MAX_INTERACTION_SIGNALS: Final[int] = 32
MAX_CONTEXT_SIZE: Final[int] = 4096


@dataclass(frozen=True)
class InteractionContext:
    profile_id: str
    signals: tuple[UserSignal, ...]
    context_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id_required")
        if len(self.signals) > MAX_INTERACTION_SIGNALS:
            raise ValueError("interaction_signal_capacity_exceeded")
        if not isinstance(self.context_id, str) or not self.context_id:
            raise ValueError("context_id_required")

    def as_prompt_context(self) -> str:
        """Return only derived signals, never source content or evidence IDs."""
        lines = [f"profile_id={self.profile_id}"]
        lines.extend(
            f"{signal.kind.value}={signal.value};confidence={signal.confidence:.2f}"
            for signal in self.signals
        )
        rendered = "\n".join(lines)
        if len(rendered.encode("utf-8")) > MAX_CONTEXT_SIZE:
            raise ValueError("interaction_context_size_exceeded")
        return rendered


def build_interaction_context(profile: UserUnderstandingProfile) -> InteractionContext:
    """Convert a validated profile into a deterministic orchestration input."""
    if not isinstance(profile, UserUnderstandingProfile):
        raise TypeError("understanding_profile_required")
    if profile.raw_content_retained:
        raise ValueError("raw_content_not_allowed")
    if len(profile.signals) > MAX_INTERACTION_SIGNALS:
        raise ValueError("interaction_signal_capacity_exceeded")

    signals = tuple(profile.signals)
    material = profile.profile_id + "|" + "|".join(
        f"{signal.kind.value}:{signal.value}:{signal.confidence:.2f}"
        for signal in signals
    )
    context_id = sha256(material.encode("utf-8")).hexdigest()
    return InteractionContext(profile.profile_id, signals, context_id)
