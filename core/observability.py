"""Structured security events and fail-closed observation pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
import time


class EventKind(str, Enum):
    AUTH_FAILURE = "auth_failure"
    IDENTITY_TAMPER = "identity_tamper"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PROCESS_ANOMALY = "process_anomaly"
    OUTBOUND_ANOMALY = "outbound_anomaly"
    SANDBOX_ESCAPE = "sandbox_escape"
    INTEGRITY_VIOLATION = "integrity_violation"
    POLICY_VIOLATION = "policy_violation"


@dataclass(frozen=True)
class ObservedEvent:
    event_id: int
    kind: EventKind
    component: str
    severity: int
    timestamp: float
    evidence_digest: str


class SecurityEventBus:
    """Bounded append-only event buffer. Consumers decide containment separately."""

    def __init__(self, *, max_events: int = 65_536) -> None:
        if not isinstance(max_events, int) or isinstance(max_events, bool) or not 1 <= max_events <= 1_000_000:
            raise ValueError("invalid_max_events")
        self._max_events = max_events
        self._events: list[ObservedEvent] = []
        self._lock = RLock()

    def publish(self, kind: EventKind, *, component: str, severity: int, evidence_digest: str) -> ObservedEvent:
        if (
            not isinstance(kind, EventKind)
            or not component
            or not isinstance(evidence_digest, str)
            or len(evidence_digest) != 64
            or any(c not in "0123456789abcdef" for c in evidence_digest)
        ):
            raise ValueError("invalid_security_event")
        if not isinstance(severity, int) or isinstance(severity, bool) or not 0 <= severity <= 100:
            raise ValueError("invalid_severity")
        with self._lock:
            if len(self._events) >= self._max_events:
                raise RuntimeError("event_capacity_exhausted")
            event = ObservedEvent(len(self._events) + 1, kind, component, severity, time.time(), evidence_digest)
            self._events.append(event)
            return event

    def snapshot(self) -> tuple[ObservedEvent, ...]:
        with self._lock:
            return tuple(self._events)
