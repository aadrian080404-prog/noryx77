"""Layered, fail-closed defense control plane for NORYX7.

This module provides policy/state primitives. Host firewalls, hypervisors,
TPMs/HSMs and network controls remain external adapters; this code never
attempts to bypass or attack external systems.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import threading
from typing import Iterable

MAX_ID = 256
MAX_LABEL = 128
MAX_COMPONENTS = 4096
MAX_SEGMENTATION_RULES = 4096


def _id(value: str, *, name: str = "id") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{name}")
    if len(value.encode("utf-8")) > MAX_ID:
        raise ValueError(f"{name}_size_exceeded")
    return value


class DefenseMode(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    LOCKDOWN = "lockdown"
    RECOVERY = "recovery"


class TrustDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ISOLATE = "isolate"


@dataclass(frozen=True)
class AccessRequest:
    principal_id: str
    component: str
    capability: str
    target: str = ""
    session_id: str = ""

    def __post_init__(self) -> None:
        _id(self.principal_id, name="principal_id")
        _id(self.component, name="component")
        _id(self.capability, name="capability")
        if self.target:
            _id(self.target, name="target")
        if self.session_id:
            _id(self.session_id, name="session_id")


@dataclass(frozen=True)
class DefenseDecision:
    decision: TrustDecision
    reason: str
    mode: DefenseMode


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    kind: str
    component: str
    severity: float
    detail: str = ""

    def __post_init__(self) -> None:
        _id(self.event_id, name="event_id")
        _id(self.kind, name="event_kind")
        _id(self.component, name="component")
        if isinstance(self.severity, bool) or not isinstance(self.severity, (int, float)) or not math.isfinite(self.severity) or not 0.0 <= self.severity <= 1.0:
            raise ValueError("invalid_severity")
        if len(self.detail.encode("utf-8")) > MAX_LABEL * 4:
            raise ValueError("detail_size_exceeded")


@dataclass(frozen=True)
class OfflineArtifact:
    artifact_id: str
    version: str
    digest: str
    encrypted: bool = True

    def __post_init__(self) -> None:
        _id(self.artifact_id, name="artifact_id")
        _id(self.version, name="version")
        if not isinstance(self.digest, str) or len(self.digest) != 64 or any(c not in "0123456789abcdef" for c in self.digest):
            raise ValueError("invalid_artifact_digest")
        if not isinstance(self.encrypted, bool):
            raise ValueError("invalid_artifact_encryption_flag")


class SegmentationPolicy:
    """Explicit, bounded allow-list for component-to-component communication."""

    def __init__(self, *, max_rules: int = MAX_SEGMENTATION_RULES) -> None:
        if isinstance(max_rules, bool) or not isinstance(max_rules, int) or max_rules <= 0 or max_rules > MAX_SEGMENTATION_RULES:
            raise ValueError("invalid_segmentation_capacity")
        self._max_rules = max_rules
        self._allowed: set[tuple[str, str]] = set()
        self._lock = threading.RLock()

    def allow(self, source: str, destination: str) -> None:
        _id(source, name="source")
        _id(destination, name="destination")
        with self._lock:
            pair = (source, destination)
            if pair not in self._allowed and len(self._allowed) >= self._max_rules:
                raise OverflowError("segmentation_capacity")
            self._allowed.add(pair)

    def revoke(self, source: str, destination: str) -> None:
        with self._lock:
            self._allowed.discard((source, destination))

    def allows(self, source: str, destination: str) -> bool:
        with self._lock:
            return (source, destination) in self._allowed


class DefenseController:
    """Central fail-closed controller for trust, isolation and recovery state."""

    def __init__(self, *, segmentation: SegmentationPolicy | None = None) -> None:
        self.segmentation = segmentation or SegmentationPolicy()
        self._mode = DefenseMode.NORMAL
        self._revoked: set[str] = set()
        self._isolated: set[str] = set()
        self._trusted_components: set[str] = set()
        self._events: list[SecurityEvent] = []
        self._lock = threading.RLock()

    @property
    def mode(self) -> DefenseMode:
        with self._lock:
            return self._mode

    def trust_component(self, component: str) -> None:
        _id(component, name="component")
        with self._lock:
            if self._mode == DefenseMode.LOCKDOWN:
                raise PermissionError("lockdown_trust_changes_denied")
            self._trusted_components.add(component)

    def revoke(self, principal_id: str) -> None:
        _id(principal_id, name="principal_id")
        with self._lock:
            self._revoked.add(principal_id)

    def isolate(self, component: str) -> None:
        _id(component, name="component")
        with self._lock:
            self._isolated.add(component)

    def restore_isolation(self, component: str) -> None:
        _id(component, name="component")
        with self._lock:
            if self._mode not in (DefenseMode.RECOVERY, DefenseMode.RESTRICTED):
                raise PermissionError("restore_requires_recovery")
            self._isolated.discard(component)

    def enter_lockdown(self, reason: str) -> None:
        _id(reason, name="lockdown_reason")
        with self._lock:
            if len(self._events) >= MAX_COMPONENTS:
                raise OverflowError("security_event_capacity")
            event = SecurityEvent(f"lockdown-{len(self._events)}", "lockdown", "security", 1.0, reason)
            self._events.append(event)
            self._mode = DefenseMode.LOCKDOWN

    def enter_recovery(self) -> None:
        with self._lock:
            if self._mode != DefenseMode.LOCKDOWN:
                raise PermissionError("recovery_requires_lockdown")
            self._mode = DefenseMode.RECOVERY

    def finish_recovery(self, *, verified_components: Iterable[str]) -> None:
        components = tuple(dict.fromkeys(verified_components))
        if not components or any(not isinstance(c, str) or not c.strip() for c in components):
            raise ValueError("verified_components_required")
        with self._lock:
            if self._mode != DefenseMode.RECOVERY:
                raise PermissionError("not_in_recovery")
            if not set(components).issubset(self._trusted_components):
                raise PermissionError("untrusted_recovery_component")
            self._mode = DefenseMode.RESTRICTED

    def resume_normal(self) -> None:
        with self._lock:
            if self._mode != DefenseMode.RESTRICTED or self._isolated:
                raise PermissionError("normal_resume_requires_clean_restricted_state")
            self._mode = DefenseMode.NORMAL

    def authorize(self, request: AccessRequest) -> DefenseDecision:
        if not isinstance(request, AccessRequest):
            raise TypeError("access_request_required")
        with self._lock:
            if request.principal_id in self._revoked:
                return DefenseDecision(TrustDecision.DENY, "principal_revoked", self._mode)
            if request.component in self._isolated:
                return DefenseDecision(TrustDecision.ISOLATE, "component_isolated", self._mode)
            if self._mode == DefenseMode.LOCKDOWN:
                return DefenseDecision(TrustDecision.DENY, "system_lockdown", self._mode)
            if self._mode == DefenseMode.RECOVERY and request.component not in self._trusted_components:
                return DefenseDecision(TrustDecision.DENY, "recovery_component_untrusted", self._mode)
            if self._mode == DefenseMode.RESTRICTED and request.capability not in {"observe", "verify", "recover"}:
                return DefenseDecision(TrustDecision.DENY, "restricted_mode", self._mode)
            if request.target and not self.segmentation.allows(request.component, request.target):
                return DefenseDecision(TrustDecision.DENY, "segmentation_denied", self._mode)
            return DefenseDecision(TrustDecision.ALLOW, "policy_ok", self._mode)

    def record_event(self, event: SecurityEvent) -> None:
        if not isinstance(event, SecurityEvent):
            raise TypeError("security_event_required")
        with self._lock:
            if len(self._events) >= MAX_COMPONENTS:
                raise OverflowError("security_event_capacity")
            self._events.append(event)

    def events(self) -> tuple[SecurityEvent, ...]:
        with self._lock:
            return tuple(self._events)


class ImmutableCoreManifest:
    """Digest-only manifest for components that must not be changed in-process."""

    def __init__(self, components: dict[str, str]) -> None:
        if not isinstance(components, dict) or not components or len(components) > MAX_COMPONENTS:
            raise ValueError("invalid_core_manifest")
        normalized: dict[str, str] = {}
        for name, digest in components.items():
            _id(name, name="component")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid_component_digest")
            normalized[name] = digest
        self._manifest = dict(normalized)
        self._digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @property
    def digest(self) -> str:
        return self._digest

    def verify(self, components: dict[str, str]) -> bool:
        return isinstance(components, dict) and components == self._manifest and hashlib.sha256(json.dumps(components, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == self._digest


class OfflineRecoveryCatalog:
    """Allow-list of offline artifacts; selection is by exact authenticated digest."""

    def __init__(self) -> None:
        self._artifacts: dict[str, OfflineArtifact] = {}

    def register(self, artifact: OfflineArtifact) -> None:
        if artifact.artifact_id in self._artifacts:
            raise ValueError("artifact_already_registered")
        self._artifacts[artifact.artifact_id] = artifact

    def verify(self, artifact_id: str, digest: str) -> bool:
        artifact = self._artifacts.get(artifact_id)
        return artifact is not None and artifact.digest == digest and artifact.encrypted
