"""Fail-closed global containment boundary for NORYX7 security incidents."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Callable

from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class LockdownState:
    mode: str
    score: int
    incidents: int
    generation: int


class SecurityLockdown:
    """Global containment state that can only be cleared through an external admin authority."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    LOCKDOWN = "lockdown"
    EMERGENCY = "emergency"

    def __init__(
        self,
        crypto: CryptoIntegrity,
        admin_authorizer: Callable[[bytes], bool],
        *,
        restricted_threshold: int = 4,
        lockdown_threshold: int = 7,
        emergency_threshold: int = 10,
    ):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        if not callable(admin_authorizer):
            raise TypeError("invalid_admin_authorizer")
        if not (
            isinstance(restricted_threshold, int)
            and isinstance(lockdown_threshold, int)
            and isinstance(emergency_threshold, int)
            and 0 < restricted_threshold < lockdown_threshold < emergency_threshold
        ):
            raise ValueError("invalid_lockdown_thresholds")
        self.crypto = crypto
        self._admin_authorizer = admin_authorizer
        self._restricted_threshold = restricted_threshold
        self._lockdown_threshold = lockdown_threshold
        self._emergency_threshold = emergency_threshold
        self._mode = self.NORMAL
        self._score = 0
        self._incidents = 0
        self._generation = 0
        self._lock = Lock()

    @property
    def state(self) -> LockdownState:
        with self._lock:
            return LockdownState(self._mode, self._score, self._incidents, self._generation)

    def record_incident(self, category: str, *, severity: int = 1) -> LockdownState:
        """Record a high-confidence security event and atomically escalate containment."""
        if not isinstance(category, str) or not category.strip():
            raise ValueError("invalid_incident_category")
        if isinstance(severity, bool) or not isinstance(severity, int) or not 1 <= severity <= 10:
            raise ValueError("invalid_incident_severity")
        with self._lock:
            self._incidents += 1
            self._score += severity
            if severity >= 10 or self._score >= self._emergency_threshold:
                self._mode = self.EMERGENCY
            elif self._score >= self._lockdown_threshold:
                self._mode = self.LOCKDOWN
            elif self._score >= self._restricted_threshold:
                self._mode = self.RESTRICTED
            self._generation += 1
            return LockdownState(self._mode, self._score, self._incidents, self._generation)

    def permits(self, *, is_admin: bool = False) -> bool:
        """Return whether the caller may use the normal runtime path."""
        with self._lock:
            if self._mode == self.NORMAL:
                return True
            return type(is_admin) is bool and is_admin

    def admin_challenge(self) -> bytes:
        """Issue a one-time challenge for an external admin authentication mechanism."""
        with self._lock:
            challenge = self.crypto.sign(
                "admin_recovery_challenge",
                {"generation": self._generation, "mode": self._mode},
                self.crypto.next_counter("admin_recovery_challenge"),
            )
            return challenge.payload + b":" + challenge.tag.encode("ascii")

    def recover(self, proof: bytes) -> LockdownState:
        """Clear containment only when the independent admin authority approves the proof."""
        if not isinstance(proof, bytes) or not proof:
            raise PermissionError("admin_recovery_denied")
        with self._lock:
            if self._mode == self.NORMAL:
                return LockdownState(self._mode, self._score, self._incidents, self._generation)
            try:
                authorized = self._admin_authorizer(proof)
            except Exception as exc:
                raise PermissionError("admin_recovery_denied") from exc
            if type(authorized) is not bool or not authorized:
                raise PermissionError("admin_recovery_denied")
            self._mode = self.NORMAL
            self._score = 0
            self._generation += 1
            return LockdownState(self._mode, self._score, self._incidents, self._generation)

    def export_seal(self) -> dict:
        """Return an authenticated state snapshot suitable for trusted persistence."""
        with self._lock:
            payload = {
                "mode": self._mode,
                "score": self._score,
                "incidents": self._incidents,
                "generation": self._generation,
            }
            counter = self.crypto.next_counter("security_lockdown_state")
            envelope = self.crypto.sign("security_lockdown_state", payload, counter)
            return {
                "domain": envelope.domain,
                "nonce": envelope.nonce,
                "counter": envelope.counter,
                "payload": envelope.payload,
                "tag": envelope.tag,
            }

    def restore_seal(self, seal: dict) -> LockdownState:
        """Restore only an authenticated state snapshot; malformed/tampered state is rejected."""
        if not isinstance(seal, dict):
            raise ValueError("invalid_lockdown_seal")
        from .crypto import CryptoEnvelope

        try:
            envelope = CryptoEnvelope(
                seal["domain"], seal["nonce"], seal["counter"], seal["payload"], seal["tag"]
            )
        except (KeyError, TypeError):
            raise ValueError("invalid_lockdown_seal")
        if not self.crypto.verify(envelope, consume=False):
            raise ValueError("invalid_lockdown_seal")
        try:
            payload = __import__("json").loads(envelope.payload.decode("utf-8"))
            mode = payload["mode"]
            score = payload["score"]
            incidents = payload["incidents"]
            generation = payload["generation"]
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise ValueError("invalid_lockdown_seal")
        if mode not in {self.NORMAL, self.RESTRICTED, self.LOCKDOWN, self.EMERGENCY}:
            raise ValueError("invalid_lockdown_seal")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (score, incidents, generation)):
            raise ValueError("invalid_lockdown_seal")
        with self._lock:
            if generation < self._generation:
                raise ValueError("stale_lockdown_seal")
            self._mode = mode
            self._score = score
            self._incidents = incidents
            self._generation = generation
            return LockdownState(self._mode, self._score, self._incidents, self._generation)
