"""Explicit JARVIS recovery state machine with fail-closed execution guards."""
from __future__ import annotations

from enum import Enum
from threading import RLock
from typing import Callable, TypeVar


class RecoveryState(str, Enum):
    NORMAL = "normal"
    INCIDENT = "incident"
    LOCKDOWN = "lockdown"
    TRUSTED_ONLY = "trusted_only"
    RECOVERY = "recovery"
    VERIFIED = "verified"


T = TypeVar("T")


class RecoveryController:
    """Monotonic, explicit recovery state machine for the standalone JARVIS front."""

    def __init__(self) -> None:
        self._state = RecoveryState.NORMAL
        self._epoch = 0
        self._lock = RLock()

    @property
    def state(self) -> RecoveryState:
        with self._lock:
            return self._state

    @property
    def epoch(self) -> int:
        with self._lock:
            return self._epoch

    def snapshot(self) -> tuple[RecoveryState, int]:
        with self._lock:
            return self._state, self._epoch

    def require_normal(self, expected_epoch: int | None = None) -> None:
        with self._lock:
            if self._state is not RecoveryState.NORMAL:
                raise PermissionError("recovery_state_denies_execution")
            if expected_epoch is not None and self._epoch != expected_epoch:
                raise PermissionError("recovery_state_changed")

    def run_if_normal(self, operation: Callable[[], T], *, expected_epoch: int | None = None) -> T:
        if not callable(operation):
            raise TypeError("operation_required")
        with self._lock:
            self.require_normal(expected_epoch=expected_epoch)
            return operation()

    def _transition(self, expected: RecoveryState, target: RecoveryState, reason: str) -> None:
        with self._lock:
            if self._state is not expected:
                raise PermissionError(reason)
            self._state = target
            self._epoch += 1

    def incident(self) -> None:
        self._transition(RecoveryState.NORMAL, RecoveryState.INCIDENT, "incident_transition_denied")

    def lockdown(self) -> None:
        self._transition(RecoveryState.INCIDENT, RecoveryState.LOCKDOWN, "lockdown_requires_incident")

    def trusted_only(self) -> None:
        self._transition(RecoveryState.LOCKDOWN, RecoveryState.TRUSTED_ONLY, "trusted_only_requires_lockdown")

    def recover(self) -> None:
        self._transition(RecoveryState.TRUSTED_ONLY, RecoveryState.RECOVERY, "recovery_requires_trusted_only")

    def verify(self, verified: bool) -> None:
        if verified is not True:
            raise PermissionError("verification_required")
        self._transition(RecoveryState.RECOVERY, RecoveryState.VERIFIED, "verification_required")

    def resume(self) -> None:
        self._transition(RecoveryState.VERIFIED, RecoveryState.NORMAL, "resume_requires_verification")
