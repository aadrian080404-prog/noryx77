from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class AudioEventType(str, Enum):
    CLAP_PATTERN = "clap_pattern"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"

@dataclass(frozen=True)
class AudioFrame:
    timestamp_ms: int
    samples: tuple[float, ...]
    sample_rate: int

@dataclass(frozen=True)
class WakeEvent:
    event_type: AudioEventType
    timestamp_ms: int
    confidence: float
    pattern: tuple[str, ...]

class ClapDetector:
    """Deterministic clap-pattern detector; it never authorizes actions."""
    def __init__(self, *, threshold: float = 0.72, min_interval_ms: int = 80, max_interval_ms: int = 700, required: tuple[str,...] = ("clap","clap")) -> None:
        if not 0.0 < threshold <= 1.0 or min_interval_ms <= 0 or max_interval_ms < min_interval_ms or not required:
            raise ValueError("invalid_clap_detector_config")
        self.threshold=threshold; self.min_interval_ms=min_interval_ms; self.max_interval_ms=max_interval_ms; self.required=required
        self._events: list[int] = []
    def reset(self) -> None: self._events.clear()
    def register_clap(self, timestamp_ms: int, confidence: float) -> WakeEvent | None:
        if timestamp_ms < 0 or not 0.0 <= confidence <= 1.0: raise ValueError("invalid_audio_event")
        if confidence < self.threshold: return None
        if self._events and not self.min_interval_ms <= timestamp_ms-self._events[-1] <= self.max_interval_ms: self._events.clear()
        self._events.append(timestamp_ms)
        if len(self._events) > len(self.required): self._events=self._events[-len(self.required):]
        if len(self._events)==len(self.required):
            result=WakeEvent(AudioEventType.CLAP_PATTERN,timestamp_ms,confidence,self.required); self.reset(); return result
        return None
