"""Small deterministic discrete-event kernel for Matrix failure experiments."""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any, Callable


@dataclass(order=True, frozen=True)
class TwinEvent:
    at: int
    sequence: int
    kind: str = field(compare=False)
    payload: Any = field(compare=False, default=None)


class DeterministicTwin:
    """Virtual-time event runner. Handlers must be deterministic and side-effect-free."""

    def __init__(self) -> None:
        self.now = 0
        self._sequence = 0
        self._queue: list[TwinEvent] = []
        self.trace: list[TwinEvent] = []

    def schedule(self, at: int, kind: str, payload: Any = None) -> TwinEvent:
        if isinstance(at, bool) or not isinstance(at, int) or at < self.now:
            raise ValueError("event_time_must_be_integer_and_not_in_past")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("event_kind_required")
        event = TwinEvent(at, self._sequence, kind, payload)
        self._sequence += 1
        heapq.heappush(self._queue, event)
        return event

    def run(self, handlers: dict[str, Callable[[TwinEvent, "DeterministicTwin"], None]],
            max_events: int = 10000) -> tuple[TwinEvent, ...]:
        if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 0:
            raise ValueError("invalid_event_budget")
        processed: list[TwinEvent] = []
        while self._queue and len(processed) < max_events:
            event = heapq.heappop(self._queue)
            self.now = event.at
            handler = handlers.get(event.kind)
            if handler is None:
                raise KeyError("missing_event_handler:" + event.kind)
            handler(event, self)
            self.trace.append(event)
            processed.append(event)
        return tuple(processed)

    @property
    def pending(self) -> int:
        return len(self._queue)
