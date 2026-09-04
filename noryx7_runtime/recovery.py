from __future__ import annotations

from core.identity import IdentityRegistry

from .attestation import AttestationVerifier
from .contracts import Attestation
from .state import JournalEntry, StateJournal


class RecoveryError(ValueError):
    """Raised when the persisted runtime journal violates its invariants."""


class RuntimeRecovery:
    """Validate and reconstruct committed execution state from an append-only journal."""

    def __init__(
        self,
        journal: StateJournal,
        verifier: AttestationVerifier | None = None,
        identity_registry: IdentityRegistry | None = None,
    ):
        if not isinstance(journal, StateJournal):
            raise TypeError("journal must be a StateJournal")
        effective_verifier = verifier if verifier is not None else journal.verifier
        effective_registry = identity_registry if identity_registry is not None else journal.identity_registry
        if effective_registry is not None and not isinstance(effective_registry, IdentityRegistry):
            raise TypeError("identity_registry must be an IdentityRegistry")
        if journal.require_signatures and effective_verifier is None:
            raise ValueError("signed journal recovery requires an attestation verifier")
        if effective_verifier is not None and not callable(getattr(effective_verifier, "verify", None)):
            raise TypeError("verifier must expose verify")
        self._journal = journal
        self._verifier = effective_verifier
        self._identity_registry = effective_registry

    def recover(self, execution_id: str) -> tuple[JournalEntry, ...]:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid execution identity")
        entries = tuple(entry for entry in self._journal.snapshot() if entry.execution_id == execution_id)
        self._validate(entries, self._verifier, self._identity_registry)
        return entries

    @staticmethod
    def _validate(
        entries: tuple[JournalEntry, ...],
        verifier: AttestationVerifier | None = None,
        identity_registry: IdentityRegistry | None = None,
    ) -> None:
        previous = -1
        seen_steps: set[str] = set()
        for entry in entries:
            if not isinstance(entry, JournalEntry):
                raise RecoveryError("invalid journal entry")
            if entry.sequence <= previous:
                raise RecoveryError("journal sequence is not strictly increasing")
            if entry.step_id in seen_steps:
                raise RecoveryError("duplicate committed step")
            fields = (
                entry.execution_id,
                entry.principal_id,
                entry.step_id,
                entry.agent_id,
                entry.agent_key_fingerprint,
                entry.action_digest,
                entry.output_digest,
            )
            if any(not isinstance(value, str) or not value for value in fields):
                raise RecoveryError("incomplete journal entry")
            for digest in (entry.agent_key_fingerprint, entry.action_digest, entry.output_digest):
                if len(digest) != 64:
                    raise RecoveryError("invalid journal digest")
                try:
                    int(digest, 16)
                except ValueError as exc:
                    raise RecoveryError("invalid journal digest") from exc
            if not isinstance(entry.signature, bytes) or len(entry.signature) != 64:
                raise RecoveryError("invalid attestation signature")
            if verifier is None:
                raise RecoveryError("attestation verifier required")
            attestation = Attestation(
                execution_id=entry.execution_id,
                principal_id=entry.principal_id,
                step_id=entry.step_id,
                agent_id=entry.agent_id,
                agent_key_fingerprint=entry.agent_key_fingerprint,
                action_digest=entry.action_digest,
                output_digest=entry.output_digest,
                verified=True,
                detail="verified",
                signature=entry.signature,
            )
            try:
                if identity_registry is not None:
                    valid = bool(identity_registry.with_trusted_identity(
                        entry.agent_id,
                        lambda identity: RuntimeRecovery._verify_with_identity(
                            identity, attestation, entry.signature, verifier
                        ),
                    ))
                else:
                    valid = bool(verifier.verify(attestation, entry.signature))
            except Exception as exc:
                raise RecoveryError("attestation verification failed") from exc
            if not valid:
                raise RecoveryError("attestation verification failed")
            previous = entry.sequence
            seen_steps.add(entry.step_id)

    @staticmethod
    def _verify_with_identity(identity, attestation, signature, verifier) -> bool:
        import hashlib

        if hashlib.sha256(identity.public_key).hexdigest() != attestation.agent_key_fingerprint:
            return False
        return bool(verifier.verify(attestation, signature))
