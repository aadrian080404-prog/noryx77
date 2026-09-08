"""Security alerting and human escalation primitives for NORYX7.

Detection produces events; policy and verification decide whether an event
becomes an alert or an emergency escalation. Delivery adapters are external.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading


MAX_TEXT = 1024


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_TEXT:
        raise ValueError(f"invalid_{name}")
    return value


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    PHONE = "phone"
    COMPUTER = "computer"
    EMERGENCY_CALL = "emergency_call"


@dataclass(frozen=True)
class SecurityAlert:
    alert_id: str
    event_id: str
    severity: AlertSeverity
    title: str
    detail: str
    channels: tuple[AlertChannel, ...]
    verified: bool = False

    def __post_init__(self) -> None:
        _text(self.alert_id, "alert_id")
        _text(self.event_id, "event_id")
        _text(self.title, "title")
        _text(self.detail, "detail")
        if not self.channels:
            raise ValueError("alert_channels_required")
        if not all(isinstance(c, AlertChannel) for c in self.channels):
            raise ValueError("invalid_alert_channel")
        if not isinstance(self.verified, bool):
            raise ValueError("invalid_alert_verification")


@dataclass(frozen=True)
class EscalationPolicy:
    """Explicit policy for human notification; emergency calls are opt-in."""
    enabled: bool = True
    call_on_critical: bool = False
    require_verified: bool = True

    def channels_for(self, severity: AlertSeverity, *, verified: bool) -> tuple[AlertChannel, ...]:
        if self.require_verified and not verified:
            return ()
        channels = [AlertChannel.PHONE, AlertChannel.COMPUTER]
        if self.enabled and self.call_on_critical and severity is AlertSeverity.CRITICAL:
            channels.append(AlertChannel.EMERGENCY_CALL)
        return tuple(channels)


class AlertRouter:
    """Queues verified alerts without performing external notification itself."""

    def __init__(self, *, policy: EscalationPolicy | None = None) -> None:
        self.policy = policy or EscalationPolicy()
        self._alerts: list[SecurityAlert] = []
        self._lock = threading.RLock()

    def create(self, *, alert_id: str, event_id: str, severity: AlertSeverity, title: str, detail: str, verified: bool) -> SecurityAlert:
        channels = self.policy.channels_for(severity, verified=verified)
        if not channels:
            raise PermissionError("alert_requires_verified_event")
        alert = SecurityAlert(alert_id, event_id, severity, title, detail, channels, verified)
        with self._lock:
            self._alerts.append(alert)
        return alert

    def alerts(self) -> tuple[SecurityAlert, ...]:
        with self._lock:
            return tuple(self._alerts)
