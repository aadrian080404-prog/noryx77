from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    sequence: int
    event_type: str
    execution_id: str
    payload_digest: str
    previous_digest: str
    digest: str


class ExecutionTrace:
    """Tamper-evident, append-only execution trace for one execution."""

    def __init__(self, execution_id: str) -> None:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id_required")
        self.execution_id = execution_id
        self._events: list[TraceEvent] = []
        self._head = "0" * 64

    @staticmethod
    def _digest(value: Any) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return sha256(encoded).hexdigest()

    def append(self, event_type: str, payload: Any) -> TraceEvent:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type_required")
        payload_digest = self._digest(payload)
        sequence = len(self._events)
        digest = self._digest(
            {
                "sequence": sequence,
                "event_type": event_type,
                "execution_id": self.execution_id,
                "payload_digest": payload_digest,
                "previous_digest": self._head,
            }
        )
        event = TraceEvent(
            sequence,
            event_type,
            self.execution_id,
            payload_digest,
            self._head,
            digest,
        )
        self._events.append(event)
        self._head = digest
        return event

    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    @property
    def head(self) -> str:
        return self._head

    def verify(self) -> bool:
        previous = "0" * 64
        for expected_sequence, event in enumerate(self._events):
            if event.sequence != expected_sequence or event.previous_digest != previous:
                return False
            expected = self._digest(
                {
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "execution_id": event.execution_id,
                    "payload_digest": event.payload_digest,
                    "previous_digest": event.previous_digest,
                }
            )
            if event.digest != expected:
                return False
            previous = event.digest
        return previous == self._head
