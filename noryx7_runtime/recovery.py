from __future__ import annotations

from .state import JournalEntry, StateJournal


class RecoveryError(ValueError):
    """Raised when the persisted runtime journal violates its invariants."""


class RuntimeRecovery:
    """Validate and reconstruct committed execution state from an append-only journal."""

    def __init__(self, journal: StateJournal):
        if not isinstance(journal, StateJournal):
            raise TypeError("journal must be a StateJournal")
        self._journal = journal

    def recover(self, execution_id: str) -> tuple[JournalEntry, ...]:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid execution identity")
        entries = tuple(entry for entry in self._journal.snapshot() if entry.execution_id == execution_id)
        self._validate(entries)
        return entries

    @staticmethod
    def _validate(entries: tuple[JournalEntry, ...]) -> None:
        previous = -1
        seen_steps: set[str] = set()
        for entry in entries:
            if not isinstance(entry, JournalEntry):
                raise RecoveryError("invalid journal entry")
            if entry.sequence <= previous:
                raise RecoveryError("journal sequence is not strictly increasing")
            if entry.step_id in seen_steps:
                raise RecoveryError("duplicate committed step")
            if not entry.execution_id or not entry.action_digest or not entry.output_digest:
                raise RecoveryError("incomplete journal entry")
            previous = entry.sequence
            seen_steps.add(entry.step_id)
