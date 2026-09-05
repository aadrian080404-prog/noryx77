"""Controlled recovery state machine for autonomous incident recovery."""
from __future__ import annotations

from enum import Enum
from threading import RLock


class RecoveryState(str, Enum):
    NORMAL = "normal"
    INCIDENT = "incident"
    LOCKDOWN = "lockdown"
    TRUSTED_ONLY = "trusted_only"
    RECOVERY = "recovery"
    VERIFIED = "verified"


_ALLOWED = {
    RecoveryState.NORMAL: {RecoveryState.INCIDENT},
    RecoveryState.INCIDENT: {RecoveryState.LOCKDOWN, RecoveryState.NORMAL},
    RecoveryState.LOCKDOWN: {RecoveryState.TRUSTED_ONLY},
    RecoveryState.TRUSTED_ONLY: {RecoveryState.RECOVERY},
    RecoveryState.RECOVERY: {RecoveryState.VERIFIED},
    RecoveryState.VERIFIED: {RecoveryState.NORMAL},
}


class RecoveryController:
    """Fail-closed recovery transitions; no direct jump around verification."""

    def __init__(self) -> None:
        self._state = RecoveryState.NORMAL
        self._lock = RLock()

    @property
    def state(self) -> RecoveryState:
        with self._lock:
            return self._state

    def transition(self, target: RecoveryState) -> RecoveryState:
        if not isinstance(target, RecoveryState):
            raise TypeError("target_must_be_RecoveryState")
        with self._lock:
            if target not in _ALLOWED[self._state]:
                raise PermissionError(f"invalid_recovery_transition:{self._state}->{target}")
            self._state = target
            return self._state

    def reset_after_verified_recovery(self) -> None:
        with self._lock:
            if self._state is not RecoveryState.VERIFIED:
                raise PermissionError("recovery_not_verified")
            self._state = RecoveryState.NORMAL
