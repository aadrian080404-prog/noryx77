"""Bounded orchestration context derived from user-understanding signals."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from .user_understanding import UserSignal, UserUnderstandingProfile

MAX_INTERACTION_SIGNALS = 32
MAX_CONTEXT_SIZE = 4096

@dataclass(frozen=True)
class InteractionContext:
    profile_id: str
    signals: tuple[UserSignal, ...]
    context_id: str
    def __post_init__(self):
        if not isinstance(self.profile_id,str) or not self.profile_id: raise ValueError("profile_id_required")
        if len(self.signals)>MAX_INTERACTION_SIGNALS: raise ValueError("interaction_signal_capacity_exceeded")
        if not isinstance(self.context_id,str) or not self.context_id: raise ValueError("context_id_required")
    def as_prompt_context(self):
        rendered="\n".join([f"profile_id={self.profile_id}"]+[f"{s.kind.value}={s.value};confidence={s.confidence:.2f}" for s in self.signals])
        if len(rendered.encode())>MAX_CONTEXT_SIZE: raise ValueError("interaction_context_size_exceeded")
        return rendered

def build_interaction_context(profile):
    if not isinstance(profile,UserUnderstandingProfile): raise TypeError("understanding_profile_required")
    if profile.raw_content_retained: raise ValueError("raw_content_not_allowed")
    if len(profile.signals)>MAX_INTERACTION_SIGNALS: raise ValueError("interaction_signal_capacity_exceeded")
    signals=tuple(profile.signals)
    material=profile.profile_id+"|"+"|".join(f"{s.kind.value}:{s.value}:{s.confidence:.2f}" for s in signals)
    return InteractionContext(profile.profile_id,signals,sha256(material.encode()).hexdigest())
