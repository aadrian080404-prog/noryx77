"""Fail-closed sandbox boundary for untrusted code and tool execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SandboxState(str, Enum):
    CREATED = "created"
    OBSERVING = "observing"
    QUARANTINED = "quarantined"
    DESTROYED = "destroyed"
    RELEASED = "released"


@dataclass(frozen=True)
class SandboxProfile:
    sandbox_id: str
    allow_network: bool = False
    allow_host_mutation: bool = False
    allow_core_access: bool = False
    allow_real_secrets: bool = False


class Sandbox:
    """State machine whose default posture denies privileged capabilities."""

    def __init__(self, profile: SandboxProfile) -> None:
        if not isinstance(profile, SandboxProfile) or not profile.sandbox_id:
            raise ValueError("invalid_sandbox_profile")
        if profile.allow_core_access or profile.allow_real_secrets or profile.allow_host_mutation:
            raise ValueError("privileged_sandbox_flags_forbidden")
        self.profile = profile
        self._state = SandboxState.CREATED

    @property
    def state(self) -> SandboxState:
        return self._state

    def observe(self) -> None:
        self._require({SandboxState.CREATED, SandboxState.OBSERVING})
        self._state = SandboxState.OBSERVING

    def quarantine(self) -> None:
        self._require({SandboxState.CREATED, SandboxState.OBSERVING})
        self._state = SandboxState.QUARANTINED

    def release(self) -> None:
        self._require({SandboxState.OBSERVING})
        self._state = SandboxState.RELEASED

    def destroy(self) -> None:
        if self._state is SandboxState.DESTROYED:
            return
        self._state = SandboxState.DESTROYED

    def authorize_network(self) -> bool:
        return self._state is SandboxState.RELEASED and self.profile.allow_network

    def _require(self, allowed: set[SandboxState]) -> None:
        if self._state not in allowed:
            raise PermissionError("invalid_sandbox_transition")
