"""Runtime identity and external attestation boundary.

NORYX7 consumes a verified claim; it does not manufacture trust locally.
Production attestation is supplied by an external trusted verifier and can be
revoked independently of cognition or agent code.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time


@dataclass(frozen=True)
class Attestation:
    runtime_id: str
    measurement: str
    issued_at: int
    expires_at: int
    nonce: str


class AttestationVerifier:
    """External trust adapter; implementations must validate a real attestation."""

    def verify(self, attestation: Attestation) -> bool:
        raise NotImplementedError


class RuntimeIdentity:
    """Fail-closed runtime identity binding with expiry and nonce freshness."""

    def __init__(self, *, verifier: AttestationVerifier, clock=time.time) -> None:
        if not isinstance(verifier, AttestationVerifier) or not callable(clock):
            raise TypeError("attestation_verifier_and_clock_required")
        self._verifier = verifier
        self._clock = clock
        self._runtime_id: str | None = None
        self._measurement: str | None = None
        self._nonce: str | None = None

    def bind(self, attestation: Attestation) -> None:
        if not isinstance(attestation, Attestation):
            raise TypeError("attestation_required")
        if not all(isinstance(v, str) and v.strip() for v in (attestation.runtime_id, attestation.measurement, attestation.nonce)):
            raise ValueError("invalid_attestation_identity")
        if len(attestation.measurement) != 64 or any(c not in "0123456789abcdef" for c in attestation.measurement):
            raise ValueError("invalid_measurement")
        if isinstance(attestation.issued_at, bool) or isinstance(attestation.expires_at, bool) or not isinstance(attestation.issued_at, int) or not isinstance(attestation.expires_at, int) or attestation.expires_at <= attestation.issued_at:
            raise ValueError("invalid_attestation_window")
        now = int(self._clock())
        if not attestation.issued_at <= now < attestation.expires_at:
            raise PermissionError("attestation_expired_or_not_yet_valid")
        try:
            verified = self._verifier.verify(attestation)
        except Exception as exc:
            raise PermissionError("attestation_verification_failed") from exc
        if verified is not True:
            raise PermissionError("attestation_verification_failed")
        self._runtime_id = attestation.runtime_id
        self._measurement = attestation.measurement
        self._nonce = attestation.nonce

    @property
    def runtime_id(self) -> str:
        if self._runtime_id is None:
            raise PermissionError("runtime_not_attested")
        return self._runtime_id

    def is_bound(self) -> bool:
        return self._runtime_id is not None and self._measurement is not None and self._nonce is not None

    def binding_digest(self) -> str:
        if not self.is_bound():
            raise PermissionError("runtime_not_attested")
        return hashlib.sha256(f"noryx7/identity/v1|{self._runtime_id}|{self._measurement}|{self._nonce}".encode()).hexdigest()
