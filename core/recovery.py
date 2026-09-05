"""Explicit recovery state machine; no implicit return to normal."""
from __future__ import annotations

from enum import Enum


class RecoveryState(str, Enum):
    NORMAL = "normal"
    INCIDENT = "incident"
    LOCKDOWN = "lockdown"
    TRUSTED_ONLY = "trusted_only"
    RECOVERY = "recovery"
    VERIFIED = "verified"


class RecoveryController:
    """Fail-closed recovery state machine with explicit trust restoration."""

    def __init__(self) -> None:
        self._state = RecoveryState.NORMAL

    @property
    def state(self) -> RecoveryState:
        return self._state

    def incident(self) -> None:
        if self._state != RecoveryState.NORMAL:
            raise PermissionError("incident_transition_denied")
        self._state = RecoveryState.INCIDENT

    def lockdown(self) -> None:
        if self._state != RecoveryState.INCIDENT:
            raise PermissionError("lockdown_requires_incident")
        self._state = RecoveryState.LOCKDOWN

    def trusted_only(self) -> None:
        if self._state != RecoveryState.LOCKDOWN:
            raise PermissionError("trusted_only_requires_lockdown")
        self._state = RecoveryState.TRUSTED_ONLY

    def recover(self) -> None:
        if self._state != RecoveryState.TRUSTED_ONLY:
            raise PermissionError("recovery_requires_trusted_only")
        self._state = RecoveryState.RECOVERY

    def verify(self, verified: bool) -> None:
        if self._state != RecoveryState.RECOVERY or verified is not True:
            raise PermissionError("verification_required")
        self._state = RecoveryState.VERIFIED

    def resume(self) -> None:
        if self._state != RecoveryState.VERIFIED:
            raise PermissionError("resume_requires_verification")
        self._state = RecoveryState.NORMAL
