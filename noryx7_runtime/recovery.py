from __future__ import annotations

from .attestation import AttestationSigner
from .contracts import Attestation
from .state import JournalEntry, StateJournal


class RecoveryError(ValueError):
    """Raised when the persisted runtime journal violates its invariants."""


class RuntimeRecovery:
    """Validate and reconstruct committed execution state from an append-only journal."""

    def __init__(self, journal: StateJournal, verifier: AttestationSigner | None = None):
        if not isinstance(journal, StateJournal):
            raise TypeError("journal must be a StateJournal")
        effective_verifier = verifier if verifier is not None else journal.verifier
        if journal.require_signatures and effective_verifier is None:
            raise ValueError("signed journal recovery requires an attestation verifier")
        if effective_verifier is not None and not callable(getattr(effective_verifier, "verify", None)):
            raise TypeError("verifier must expose verify")
        self._journal = journal
        self._verifier = effective_verifier

    def recover(self, execution_id: str) -> tuple[JournalEntry, ...]:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid execution identity")
        entries = tuple(entry for entry in self._journal.snapshot() if entry.execution_id == execution_id)
        self._validate(entries, self._verifier)
        return entries

    @staticmethod
    def _validate(entries: tuple[JournalEntry, ...], verifier: AttestationSigner | None = None) -> None:
        previous = -1
        seen_steps: set[str] = set()
        for entry in entries:
            if not isinstance(entry, JournalEntry):
                raise RecoveryError("invalid journal entry")
            if entry.sequence <= previous:
                raise RecoveryError("journal sequence is not strictly increasing")
            if entry.step_id in seen_steps:
                raise RecoveryError("duplicate committed step")
            fields = (entry.execution_id, entry.principal_id, entry.step_id, entry.agent_id, entry.action_digest, entry.output_digest)
            if any(not isinstance(value, str) or not value for value in fields):
                raise RecoveryError("incomplete journal entry")
            if not isinstance(entry.signature, bytes) or len(entry.signature) != 64:
                raise RecoveryError("invalid attestation signature")
            if verifier is None:
                raise RecoveryError("attestation verifier required")
            attestation = Attestation(
                execution_id=entry.execution_id,
                principal_id=entry.principal_id,
                step_id=entry.step_id,
                agent_id=entry.agent_id,
                action_digest=entry.action_digest,
                output_digest=entry.output_digest,
                verified=True,
                detail="verified",
                signature=entry.signature,
            )
            try:
                valid = bool(verifier.verify(attestation, entry.signature))
            except Exception as exc:
                raise RecoveryError("attestation verification failed") from exc
            if not valid:
                raise RecoveryError("attestation verification failed")
            previous = entry.sequence
            seen_steps.add(entry.step_id)
