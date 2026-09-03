from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from .contracts import Attestation


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    execution_id: str
    principal_id: str
    step_id: str
    agent_id: str
    action_digest: str
    output_digest: str
    signature: bytes


class StateJournal:
    """Append-only commit boundary with identity and replay protection."""

    def __init__(self, *, require_signatures: bool = True) -> None:
        if not isinstance(require_signatures, bool):
            raise TypeError("require_signatures must be bool")
        self._lock = RLock()
        self._entries: list[JournalEntry] = []
        self._keys: set[tuple[str, str]] = set()
        self._require_signatures = require_signatures

    def append(self, attestation: Attestation) -> JournalEntry:
        if not isinstance(attestation, Attestation):
            raise TypeError("attestation must be an Attestation")
        if not attestation.verified:
            raise PermissionError("cannot commit unverified result")
        fields = (
            attestation.execution_id,
            attestation.principal_id,
            attestation.step_id,
            attestation.agent_id,
            attestation.action_digest,
            attestation.output_digest,
        )
        if any(not isinstance(value, str) or not value for value in fields):
            raise ValueError("incomplete attestation")
        if self._require_signatures and (not isinstance(attestation.signature, bytes) or len(attestation.signature) != 64):
            raise PermissionError("cannot commit unsigned attestation")
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
                action_digest=attestation.action_digest,
                output_digest=attestation.output_digest,
                signature=attestation.signature,
            )
            self._entries.append(entry)
            self._keys.add(key)
            return entry

    def snapshot(self) -> tuple[JournalEntry, ...]:
        with self._lock:
            return tuple(self._entries)
