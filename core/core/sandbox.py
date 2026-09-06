"""Fail-closed sandbox lifecycle primitives."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
MAX_ID = 256
class SandboxState(str, Enum):
    CREATED = "created"
    OBSERVING = "observing"
    QUARANTINED = "quarantined"
    DESTROYED = "destroyed"
    RELEASED = "released"
@dataclass(frozen=True)
class SandboxSpec:
    sandbox_id: str
    workload_digest: str
    network_allowed: bool = False
    host_mutation_allowed: bool = False
    core_access_allowed: bool = False
    def __post_init__(self) -> None:
        if not isinstance(self.sandbox_id, str) or not self.sandbox_id.strip() or len(self.sandbox_id.encode()) > MAX_ID:
            raise ValueError("invalid_sandbox_id")
        if not isinstance(self.workload_digest, str) or len(self.workload_digest) != 64 or any(c not in "0123456789abcdef" for c in self.workload_digest):
            raise ValueError("invalid_workload_digest")
        if self.network_allowed or self.host_mutation_allowed or self.core_access_allowed:
            raise ValueError("unsafe_sandbox_capability")
class Sandbox:
    def __init__(self, spec: SandboxSpec) -> None:
        self.spec = spec
        self._state = SandboxState.CREATED
    @property
    def state(self) -> SandboxState:
        return self._state
    def observe(self) -> None:
        if self._state != SandboxState.CREATED:
            raise PermissionError("sandbox_observe_invalid_state")
        self._state = SandboxState.OBSERVING
    def quarantine(self) -> None:
        if self._state not in (SandboxState.CREATED, SandboxState.OBSERVING):
            raise PermissionError("sandbox_quarantine_invalid_state")
        self._state = SandboxState.QUARANTINED
    def destroy(self) -> None:
        if self._state == SandboxState.RELEASED:
            raise PermissionError("released_sandbox_cannot_destroy")
        self._state = SandboxState.DESTROYED
    def release_verified(self) -> None:
        if self._state != SandboxState.OBSERVING:
            raise PermissionError("sandbox_release_requires_observation")
        self._state = SandboxState.RELEASED
