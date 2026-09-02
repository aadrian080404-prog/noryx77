"""Fail-closed global containment boundary for NORYX7 security incidents."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from typing import Callable
import json

from .crypto import CryptoIntegrity, CryptoEnvelope


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
    STATE_DOMAIN = "security_lockdown_state"

    def __init__(self, crypto: CryptoIntegrity, admin_authorizer: Callable[[bytes], bool], *, restricted_threshold: int = 4, lockdown_threshold: int = 7, emergency_threshold: int = 10, state_store=None):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        if not callable(admin_authorizer):
            raise TypeError("invalid_admin_authorizer")
        if not (isinstance(restricted_threshold, int) and isinstance(lockdown_threshold, int) and isinstance(emergency_threshold, int) and 0 < restricted_threshold < lockdown_threshold < emergency_threshold):
            raise ValueError("invalid_lockdown_thresholds")
        if state_store is not None and not (callable(getattr(state_store, "load", None)) and callable(getattr(state_store, "save", None))):
            raise TypeError("invalid_lockdown_state_store")
        self.crypto = crypto
        self._admin_authorizer = admin_authorizer
        self._state_store = state_store
        self._restricted_threshold = restricted_threshold
        self._lockdown_threshold = lockdown_threshold
        self._emergency_threshold = emergency_threshold
        self._mode = self.NORMAL
        self._score = 0
        self._incidents = 0
        self._generation = 0
        self._issued_challenges: set[bytes] = set()
        self._lock = RLock()
        if self._state_store is not None:
            persisted = self._state_store.load()
            if persisted is not None:
                self.restore_seal(persisted)
            else:
                self._state_store.save(self.export_seal())

    @property
    def state(self) -> LockdownState:
        with self._lock:
            return LockdownState(self._mode, self._score, self._incidents, self._generation)

    @contextmanager
    def execution_guard(self):
        """Atomically authorize one final execution boundary against lockdown changes.

        The lock is held across the final permit check and the caller's execution.
        Concurrent incident transitions therefore linearize either before the action
        or after it, never between the final check and the handler invocation.
        RLock keeps same-thread containment reporting from deadlocking.
        """
        with self._lock:
            if self._mode != self.NORMAL:
                raise PermissionError("global_lockdown")
            yield

    def _persist(self, *, expected_generation: int | None = None) -> None:
        if self._state_store is not None:
            seal = self.export_seal()
            if expected_generation is None:
                self._state_store.save(seal)
            else:
                try:
                    self._state_store.save(seal, expected_generation=expected_generation)
                except TypeError as exc:
                    raise ValueError("lockdown_store_conflict") from exc

    def _fail_closed_after_persistence_failure(self) -> None:
        with self._lock:
            self._mode = self.EMERGENCY
            self._issued_challenges.clear()

    def record_incident(self, category: str, *, severity: int = 1) -> LockdownState:
        if not isinstance(category, str) or not category.strip():
            raise ValueError("invalid_incident_category")
        if isinstance(severity, bool) or not isinstance(severity, int) or not 1 <= severity <= 10:
            raise ValueError("invalid_incident_severity")
        with self._lock:
            previous_generation = self._generation
            self._incidents += 1
            self._score += severity
            if severity >= 10 or self._score >= self._emergency_threshold:
                self._mode = self.EMERGENCY
            elif self._score >= self._lockdown_threshold:
                self._mode = self.LOCKDOWN
            elif self._score >= self._restricted_threshold:
                self._mode = self.RESTRICTED
            self._generation += 1
            state = LockdownState(self._mode, self._score, self._incidents, self._generation)
        try:
            self._persist(expected_generation=previous_generation)
        except Exception:
            self._fail_closed_after_persistence_failure()
            raise
        return state

    def permits(self, *, is_admin: bool = False) -> bool:
        with self._lock:
            if self._mode == self.NORMAL:
                return True
            return type(is_admin) is bool and is_admin

    def admin_challenge(self) -> bytes:
        """Issue a cryptographically authenticated, single-use recovery challenge."""
        with self._lock:
            challenge = self.crypto.sign("admin_recovery_challenge", {"generation": self._generation, "mode": self._mode}, self.crypto.next_counter("admin_recovery_challenge"))
            encoded = challenge.payload + b":" + challenge.tag.encode("ascii")
            self._issued_challenges.add(sha256(encoded).digest())
            return encoded

    def recover(self, proof: bytes) -> LockdownState:
        """Clear containment only for an issued, unused challenge approved externally."""
        if not isinstance(proof, bytes) or not proof:
            raise PermissionError("admin_recovery_denied")
        proof_id = sha256(proof).digest()
        with self._lock:
            if self._mode == self.NORMAL:
                return LockdownState(self._mode, self._score, self._incidents, self._generation)
            if proof_id not in self._issued_challenges:
                raise PermissionError("admin_recovery_denied")
            authorization_generation = self._generation
            authorization_mode = self._mode

        try:
            authorized = self._admin_authorizer(proof)
        except Exception as exc:
            raise PermissionError("admin_recovery_denied") from exc
        if type(authorized) is not bool or not authorized:
            raise PermissionError("admin_recovery_denied")

        with self._lock:
            if self._mode == self.NORMAL:
                raise PermissionError("admin_recovery_denied")
            if self._generation != authorization_generation or self._mode != authorization_mode:
                raise PermissionError("admin_recovery_denied")
            if proof_id not in self._issued_challenges:
                raise PermissionError("admin_recovery_denied")
            self._issued_challenges.remove(proof_id)
            self._mode = self.NORMAL
            self._score = 0
            self._generation += 1
            state = LockdownState(self._mode, self._score, self._incidents, self._generation)
        try:
            self._persist(expected_generation=authorization_generation)
        except Exception as exc:
            self._fail_closed_after_persistence_failure()
            if isinstance(exc, ValueError) and str(exc) == "lockdown_store_conflict":
                raise PermissionError("admin_recovery_denied") from exc
            raise
        return state

    def export_seal(self) -> dict:
        with self._lock:
            payload = {"mode": self._mode, "score": self._score, "incidents": self._incidents, "generation": self._generation}
            envelope = self.crypto.sign(self.STATE_DOMAIN, payload, self.crypto.next_counter(self.STATE_DOMAIN))
            return {"domain": envelope.domain, "nonce": envelope.nonce, "counter": envelope.counter, "payload": envelope.payload, "tag": envelope.tag}

    def restore_seal(self, seal: dict) -> LockdownState:
        if not isinstance(seal, dict):
            raise ValueError("invalid_lockdown_seal")
        try:
            envelope = CryptoEnvelope(seal["domain"], seal["nonce"], seal["counter"], seal["payload"], seal["tag"])
        except (KeyError, TypeError):
            raise ValueError("invalid_lockdown_seal")
        if envelope.domain != self.STATE_DOMAIN:
            raise ValueError("invalid_lockdown_seal")
        if not self.crypto.verify(envelope, consume=False):
            raise ValueError("invalid_lockdown_seal")
        try:
            payload = json.loads(envelope.payload.decode("utf-8"))
            mode, score, incidents, generation = payload["mode"], payload["score"], payload["incidents"], payload["generation"]
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise ValueError("invalid_lockdown_seal")
        if mode not in {self.NORMAL, self.RESTRICTED, self.LOCKDOWN, self.EMERGENCY}:
            raise ValueError("invalid_lockdown_seal")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (score, incidents, generation)):
            raise ValueError("invalid_lockdown_seal")
        with self._lock:
            if generation < self._generation:
                raise ValueError("stale_lockdown_seal")
            self._mode, self._score, self._incidents, self._generation = mode, score, incidents, generation
            self._issued_challenges.clear()
            return LockdownState(self._mode, self._score, self._incidents, self._generation)
