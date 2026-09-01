"""Per-run cryptographic session boundary for HYPERSYNTH attestations."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from typing import Any

from .attestation import HypersynthAttestation, StageAttestation
from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    task_id: str
    risk_class: str
    verification_requirements: tuple[str, ...]


class AttestationSession:
    """Fail-closed per-task session with authenticated stage ownership and one-use evidence."""

    MAX_SESSION_ID_LENGTH = 64

    def __init__(self, crypto: CryptoIntegrity, task_id: str, risk_class: str,
                 verification_requirements: tuple[str, ...],
                 *, session_id: str | None = None):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("invalid_session_task_id")
        if not isinstance(risk_class, str) or not risk_class.strip():
            raise ValueError("invalid_session_risk_class")
        if not isinstance(verification_requirements, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in verification_requirements
        ):
            raise ValueError("invalid_session_verification_requirements")
        session_id = secrets.token_hex(16) if session_id is None else session_id
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > self.MAX_SESSION_ID_LENGTH:
            raise ValueError("invalid_session_id")
        self.crypto = crypto
        self.context = SessionContext(session_id, task_id, risk_class, verification_requirements)
        self.attestation = HypersynthAttestation(crypto)
        self._consumed: set[str] = set()
        self._closed = False
        self._context_tag = crypto.digest("hypersynth_session", {
            "session_id": session_id,
            "task_id": task_id,
            "risk_class": risk_class,
            "verification_requirements": verification_requirements,
        })

    @property
    def session_id(self) -> str:
        return self.context.session_id

    @property
    def context_tag(self) -> str:
        return self._context_tag

    @property
    def closed(self) -> bool:
        return self._closed

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("attestation_session_closed")

    def attest(self, stage: str, payload: Any) -> StageAttestation:
        self._check_open()
        body = {
            "session_id": self.session_id,
            "context_tag": self._context_tag,
            "payload": payload,
        }
        return self.attestation.attest_stage(
            self.context.task_id, stage, self.context.risk_class,
            self.context.verification_requirements, body,
        )

    def verify(self, attestation: StageAttestation, stage: str, payload: Any, *, consume: bool = True) -> bool:
        if self._closed:
            return False
        if not isinstance(attestation, StageAttestation) or attestation.stage != stage:
            return False
        if attestation.tag in self._consumed:
            return False
        body = {"session_id": self.session_id, "context_tag": self._context_tag, "payload": payload}
        if not self.attestation.verify_stage(attestation, body):
            return False
        if consume:
            self._consumed.add(attestation.tag)
        return True

    def close(self) -> None:
        self._closed = True

    def verify_context(self, context: SessionContext) -> bool:
        if self._closed or not isinstance(context, SessionContext):
            return False
        payload = {
            "session_id": context.session_id,
            "task_id": context.task_id,
            "risk_class": context.risk_class,
            "verification_requirements": context.verification_requirements,
        }
        expected = self.crypto.digest("hypersynth_session", payload)
        return context == self.context and hmac.compare_digest(expected, self._context_tag)
