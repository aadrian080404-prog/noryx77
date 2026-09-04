from __future__ import annotations

import hashlib
from dataclasses import dataclass
from threading import RLock
from typing import Protocol

from core.identity import IdentityRegistry

from .contracts import Attestation


class AttestationVerifier(Protocol):
    def verify(self, attestation: Attestation, signature: bytes) -> bool:
        ...


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    execution_id: str
    principal_id: str
    step_id: str
    agent_id: str
    agent_key_fingerprint: str
    action_digest: str
    output_digest: str
    signature: bytes


class StateJournal:
    """Append-only commit boundary with authenticity and atomic identity trust."""

    def __init__(
        self,
        *,
        require_signatures: bool = True,
        verifier: AttestationVerifier | None = None,
        identity_registry: IdentityRegistry | None = None,
    ) -> None:
        if not isinstance(require_signatures, bool):
            raise TypeError("require_signatures must be bool")
        if require_signatures and verifier is None:
            raise ValueError("signed journal requires an attestation verifier")
        if verifier is not None and not callable(getattr(verifier, "verify", None)):
            raise TypeError("verifier must expose verify")
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise TypeError("identity_registry must be an IdentityRegistry")
        self._lock = RLock()
        self._entries: list[JournalEntry] = []
        self._keys: set[tuple[str, str]] = set()
        self._require_signatures = require_signatures
        self._verifier = verifier
        self._identity_registry = identity_registry

    @property
    def verifier(self) -> AttestationVerifier | None:
        return self._verifier

    @property
    def require_signatures(self) -> bool:
        return self._require_signatures

    def append(self, attestation: Attestation) -> JournalEntry:
        self._validate_attestation(attestation)
        if self._identity_registry is not None:
            return self._identity_registry.with_trusted_identity(
                attestation.agent_id,
                lambda identity: self._append_verified(attestation, identity.public_key),
            )
        return self._append_verified(attestation, None)

    def _append_verified(self, attestation: Attestation, trusted_public_key: bytes | None) -> JournalEntry:
        if trusted_public_key is not None:
            expected_fingerprint = hashlib.sha256(trusted_public_key).hexdigest()
            if attestation.agent_key_fingerprint != expected_fingerprint:
                raise PermissionError("attestation key fingerprint is not trusted")
        if self._require_signatures:
            try:
                valid = bool(self._verifier.verify(attestation, attestation.signature))
            except Exception as exc:
                raise PermissionError("invalid attestation signature") from exc
            if not valid:
                raise PermissionError("invalid attestation signature")
        key = (attestation.execution_id, attestation.step_id)
        with self._lock:
            if key in self._keys:
                raise ValueError("duplicate execution step")
            entry = JournalEntry(
                sequence=len(self._entries),
                execution_id=attestation.execution_id,
                principal_id=attestation.principal_id,
                step_id=attestation.step_id,
                agent_id=attestation.agent_id,
                agent_key_fingerprint=attestation.agent_key_fingerprint,
                action_digest=attestation.action_digest,
                output_digest=attestation.output_digest,
                signature=attestation.signature,
            )
            self._entries.append(entry)
            self._keys.add(key)
            return entry

    @staticmethod
    def _validate_attestation(attestation: Attestation) -> None:
        if not isinstance(attestation, Attestation):
            raise TypeError("attestation must be an Attestation")
        fields = (
            attestation.execution_id,
            attestation.principal_id,
            attestation.step_id,
            attestation.agent_id,
            attestation.agent_key_fingerprint,
            attestation.action_digest,
            attestation.output_digest,
        )
        if any(not isinstance(value, str) or not value for value in fields):
            raise ValueError("incomplete attestation")
        if not attestation.verified:
            raise PermissionError("cannot commit unverified result")
        for digest in (attestation.agent_key_fingerprint, attestation.action_digest, attestation.output_digest):
            if len(digest) != 64:
                raise ValueError("attestation digest must be SHA-256 hex")
            try:
                int(digest, 16)
            except ValueError as exc:
                raise ValueError("attestation digest is not hexadecimal") from exc
        if self._require_signatures and (not isinstance(attestation.signature, bytes) or len(attestation.signature) != 64):
            raise PermissionError("cannot commit unsigned attestation")

    def snapshot(self) -> tuple[JournalEntry, ...]:
        with self._lock:
            return tuple(self._entries)
