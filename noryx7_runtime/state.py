from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from .contracts import Attestation


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    execution_id: str
    step_id: str
    action_digest: str
    output_digest: str


class StateJournal:
    """Small append-only state boundary for the real runtime.

    Entries are immutable and sequenced under a lock. The journal is an
    observation/commit boundary, not an authorization mechanism.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._entries: list[JournalEntry] = []

    def append(self, attestation: Attestation) -> JournalEntry:
        if not attestation.verified:
            raise PermissionError("cannot commit unverified result")
        with self._lock:
            entry = JournalEntry(
                sequence=len(self._entries),
                execution_id=attestation.execution_id,
                step_id=attestation.step_id,
                action_digest=attestation.action_digest,
                output_digest=attestation.output_digest,
            )
            self._entries.append(entry)
            return entry

    def snapshot(self) -> tuple[JournalEntry, ...]:
        with self._lock:
            return tuple(self._entries)
