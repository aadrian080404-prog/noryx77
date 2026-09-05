"""Consent-bound, bounded user-understanding signals."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import re

MAX_CONTENT_ITEMS = 4096
MAX_CONTENT_SIZE = 256 * 1024
MAX_SIGNALS = 128
MAX_VALUE_SIZE = 256

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
    def __post_init__(self):
        if not isinstance(self.content_id, str) or not self.content_id.strip(): raise ValueError("invalid_content_id")
        if len(self.content_id.encode("utf-8")) > MAX_VALUE_SIZE: raise ValueError("content_id_too_large")
        if not isinstance(self.text, str) or not self.text.strip(): raise ValueError("content_required")
        if len(self.text.encode("utf-8")) > MAX_CONTENT_SIZE: raise ValueError("content_size_exceeded")
        if not isinstance(self.source, str) or not self.source.strip() or len(self.source.encode("utf-8")) > MAX_VALUE_SIZE: raise ValueError("invalid_content_source")

@dataclass(frozen=True)
class UserSignal:
    kind: SignalKind
    value: str
    confidence: float
    evidence_ids: tuple[str, ...]
    def __post_init__(self):
        if not isinstance(self.kind, SignalKind): raise ValueError("invalid_signal_kind")
        if not isinstance(self.value, str) or not self.value.strip() or len(self.value.encode("utf-8")) > MAX_VALUE_SIZE: raise ValueError("invalid_signal_value")
        if isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0: raise ValueError("invalid_signal_confidence")
        if not isinstance(self.evidence_ids, tuple) or not self.evidence_ids or len(self.evidence_ids) > MAX_SIGNALS: raise ValueError("signal_evidence_required")
        if any(not isinstance(item, str) or not item.strip() or len(item.encode("utf-8")) > MAX_VALUE_SIZE for item in self.evidence_ids): raise ValueError("invalid_signal_evidence")

@dataclass(frozen=True)
class UserUnderstandingProfile:
    profile_id: str
    signals: tuple[UserSignal, ...]
    content_count: int
    raw_content_retained: bool = False
    def __post_init__(self):
        if not isinstance(self.profile_id, str) or not self.profile_id.strip(): raise ValueError("profile_id_required")
        if not isinstance(self.signals, tuple) or len(self.signals) > MAX_SIGNALS: raise ValueError("signal_capacity_exceeded")
        if any(not isinstance(s, UserSignal) for s in self.signals): raise TypeError("user_signal_required")
        if isinstance(self.content_count, bool) or not isinstance(self.content_count, int) or not 0 <= self.content_count <= MAX_CONTENT_ITEMS: raise ValueError("invalid_content_count")
        if not isinstance(self.raw_content_retained, bool): raise ValueError("invalid_raw_content_flag")

class UserUnderstandingEngine:
    _TOPICS = ("programming","software","architecture","engineering","science","finance","economics","business","travel","writing","research","design","security","automation")
    _FORMATS = ("short","detailed","step_by_step","table","bullet_points","example_driven")
    _TONES = ("direct","formal","friendly","technical","concise","exploratory")
    _WORKFLOWS = ("planning","debugging","comparison","research","execution","verification")
    def __init__(self, *, consent: UnderstandingConsent):
        if not isinstance(consent, UnderstandingConsent): raise ValueError("understanding_consent_required")
        self.consent = consent
    @staticmethod
    def _evidence_id(item): return sha256((item.content_id + "\x00" + item.source).encode()).hexdigest()
    @staticmethod
    def _contains(text, term): return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I) is not None
    def _extract(self, item):
        evidence=(self._evidence_id(item),); text=item.text; out=[]
        for term in self._TOPICS:
            if self._contains(text,term): out.append(UserSignal(SignalKind.TOPIC,term,.70,evidence))
        for term in self._FORMATS:
            if self._contains(text,term.replace("_"," ")): out.append(UserSignal(SignalKind.FORMAT,term,.80,evidence))
        for term in self._TONES:
            if self._contains(text,term): out.append(UserSignal(SignalKind.TONE,term,.70,evidence))
        for term in self._WORKFLOWS:
            if self._contains(text,term): out.append(UserSignal(SignalKind.WORKFLOW,term,.70,evidence))
        words=len(text.split())
        if words<=80: out.append(UserSignal(SignalKind.VERBOSITY,"concise_content",.60,evidence))
        elif words>=400: out.append(UserSignal(SignalKind.VERBOSITY,"detailed_content",.60,evidence))
        return out
    def build_profile(self, contents):
        if self.consent is UnderstandingConsent.DENIED: raise PermissionError("user_understanding_consent_denied")
        if not isinstance(contents, tuple) or len(contents)>MAX_CONTENT_ITEMS: raise ValueError("content_capacity_exceeded")
        if any(not isinstance(x,UserContent) for x in contents): raise TypeError("user_content_required")
        collected={}
        for item in contents:
            for signal in self._extract(item):
                key=(signal.kind,signal.value); prev=collected.get(key)
                if prev is None: collected[key]=signal
                else:
                    ids=tuple(dict.fromkeys(prev.evidence_ids+signal.evidence_ids))
                    collected[key]=UserSignal(signal.kind,signal.value,min(1.,prev.confidence+.05),ids)
                if len(collected)>MAX_SIGNALS:
                    raise ValueError("signal_capacity_exceeded")
        signals=tuple(sorted(collected.values(),key=lambda s:(s.kind.value,s.value)))
        profile_id=sha256("|".join(f"{s.kind.value}:{s.value}" for s in signals).encode()).hexdigest()
        return UserUnderstandingProfile(profile_id,signals,len(contents),False)
    def prepare_first_interaction(self, profile):
        if self.consent is UnderstandingConsent.DENIED: raise PermissionError("user_understanding_consent_denied")
        if not isinstance(profile,UserUnderstandingProfile) or profile.raw_content_retained: raise ValueError("invalid_understanding_profile")
        return profile.signals
