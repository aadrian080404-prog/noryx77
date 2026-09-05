"""Consent-bound pre-interaction user understanding for NORYX7.

The engine can study user-provided content before the first live interaction,
but only inside an explicit consent boundary. It extracts non-sensitive,
interaction-relevant signals (topics, format, tone, verbosity and workflow
preferences), keeps confidence and provenance, and never persists raw content.
It does not infer health, religion, politics, sexuality, race, financial status,
or other sensitive traits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import re
from typing import Final

MAX_CONTENT_ITEMS: Final[int] = 4096
MAX_CONTENT_SIZE: Final[int] = 256 * 1024
MAX_SIGNALS: Final[int] = 128
MAX_VALUE_SIZE: Final[int] = 256


class UnderstandingConsent(str, Enum):
    DENIED = "denied"
    PRE_INTERACTION = "pre_interaction"
    CONTINUOUS = "continuous"


class SignalKind(str, Enum):
    TOPIC = "topic"
    FORMAT = "format"
    TONE = "tone"
    VERBOSITY = "verbosity"
    WORKFLOW = "workflow"


@dataclass(frozen=True)
class UserContent:
    content_id: str
    text: str
    source: str = "user_provided"

    def __post_init__(self) -> None:
        if not isinstance(self.content_id, str) or not self.content_id.strip():
            raise ValueError("invalid_content_id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("content_required")
        if len(self.text.encode("utf-8")) > MAX_CONTENT_SIZE:
            raise ValueError("content_size_exceeded")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("invalid_content_source")


@dataclass(frozen=True)
class UserSignal:
    kind: SignalKind
    value: str
    confidence: float
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SignalKind):
            raise ValueError("invalid_signal_kind")
        if not isinstance(self.value, str) or not self.value.strip() or len(self.value.encode("utf-8")) > MAX_VALUE_SIZE:
            raise ValueError("invalid_signal_value")
        if isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("invalid_signal_confidence")
        if not isinstance(self.evidence_ids, tuple) or not self.evidence_ids:
            raise ValueError("signal_evidence_required")


@dataclass(frozen=True)
class UserUnderstandingProfile:
    profile_id: str
    signals: tuple[UserSignal, ...]
    content_count: int
    raw_content_retained: bool = False


class UserUnderstandingEngine:
    """Builds a bounded interaction profile from explicitly supplied content."""

    _TOPICS = (
        "programming", "software", "architecture", "engineering", "science",
        "finance", "economics", "business", "travel", "writing", "research",
        "design", "security", "automation",
    )
    _FORMATS = ("short", "detailed", "step_by_step", "table", "bullet_points", "example_driven")
    _TONES = ("direct", "formal", "friendly", "technical", "concise", "exploratory")
    _WORKFLOWS = ("planning", "debugging", "comparison", "research", "execution", "verification")

    def __init__(self, *, consent: UnderstandingConsent) -> None:
        if not isinstance(consent, UnderstandingConsent):
            raise ValueError("understanding_consent_required")
        self.consent = consent

    @staticmethod
    def _evidence_id(item: UserContent) -> str:
        return sha256((item.content_id + "\x00" + item.source).encode("utf-8")).hexdigest()

    @staticmethod
    def _contains(text: str, term: str) -> bool:
        return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) is not None

    def _extract(self, item: UserContent) -> list[UserSignal]:
        text = item.text
        evidence = (self._evidence_id(item),)
        signals: list[UserSignal] = []
        for term in self._TOPICS:
            if self._contains(text, term):
                signals.append(UserSignal(SignalKind.TOPIC, term, 0.70, evidence))
        for term in self._FORMATS:
            if self._contains(text, term.replace("_", " ")):
                signals.append(UserSignal(SignalKind.FORMAT, term, 0.80, evidence))
        for term in self._TONES:
            if self._contains(text, term):
                signals.append(UserSignal(SignalKind.TONE, term, 0.70, evidence))
        for term in self._WORKFLOWS:
            if self._contains(text, term):
                signals.append(UserSignal(SignalKind.WORKFLOW, term, 0.70, evidence))
        word_count = len(text.split())
        if word_count <= 80:
            signals.append(UserSignal(SignalKind.VERBOSITY, "concise_content", 0.60, evidence))
        elif word_count >= 400:
            signals.append(UserSignal(SignalKind.VERBOSITY, "detailed_content", 0.60, evidence))
        return signals

    def build_profile(self, contents: tuple[UserContent, ...]) -> UserUnderstandingProfile:
        if self.consent is UnderstandingConsent.DENIED:
            raise PermissionError("user_understanding_consent_denied")
        if not isinstance(contents, tuple) or len(contents) > MAX_CONTENT_ITEMS:
            raise ValueError("content_capacity_exceeded")
        if any(not isinstance(item, UserContent) for item in contents):
            raise TypeError("user_content_required")

        collected: dict[tuple[SignalKind, str], UserSignal] = {}
        for item in contents:
            for signal in self._extract(item):
                key = (signal.kind, signal.value)
                previous = collected.get(key)
                if previous is None or signal.confidence > previous.confidence:
                    collected[key] = signal
                elif previous is not None:
                    ids = tuple(dict.fromkeys(previous.evidence_ids + signal.evidence_ids))
                    collected[key] = UserSignal(signal.kind, signal.value, min(1.0, previous.confidence + 0.05), ids)
                if len(collected) >= MAX_SIGNALS:
                    break
            if len(collected) >= MAX_SIGNALS:
                break

        signals = tuple(sorted(collected.values(), key=lambda s: (s.kind.value, s.value)))
        material = "|".join(f"{s.kind.value}:{s.value}" for s in signals)
        profile_id = sha256(material.encode("utf-8")).hexdigest()
        return UserUnderstandingProfile(profile_id, signals, len(contents), raw_content_retained=False)

    def prepare_first_interaction(self, profile: UserUnderstandingProfile) -> tuple[UserSignal, ...]:
        if self.consent is UnderstandingConsent.DENIED:
            raise PermissionError("user_understanding_consent_denied")
        if not isinstance(profile, UserUnderstandingProfile) or profile.raw_content_retained:
            raise ValueError("invalid_understanding_profile")
        return profile.signals
