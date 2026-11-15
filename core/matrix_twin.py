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


@dataclass(frozen=True)
class NetworkMessage:
    message_id: str
    source: str
    destination: str
    payload: Any


class DeterministicNetwork:
    """Deterministic message transport with latency, partitions and drop traces.

    This is a test model, not a real network transport or consensus implementation.
    """
    def __init__(self, twin: DeterministicTwin) -> None:
        self.twin = twin
        self._partitions: set[frozenset[str]] = set()
        self.delivered: list[NetworkMessage] = []
        self.dropped: list[NetworkMessage] = []

    @staticmethod
    def _link(source: str, destination: str) -> frozenset[str]:
        if (not isinstance(source, str) or not source.strip()
                or not isinstance(destination, str) or not destination.strip()
                or source == destination):
            raise ValueError("distinct_network_endpoints_required")
        return frozenset((source, destination))

    def partition(self, source: str, destination: str) -> None:
        self._partitions.add(self._link(source, destination))

    def heal(self, source: str, destination: str) -> None:
        self._partitions.discard(self._link(source, destination))

    def send(self, message_id: str, source: str, destination: str,
             payload: Any, delay: int = 0) -> TwinEvent:
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError("message_id_required")
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ValueError("network_delay_must_be_nonnegative_integer")
        self._link(source, destination)
        message = NetworkMessage(message_id, source, destination, payload)
        return self.twin.schedule(self.twin.now + delay, "network_delivery", message)

    def run(self, max_events: int = 10000) -> tuple[TwinEvent, ...]:
        def deliver(event: TwinEvent, _sim: DeterministicTwin) -> None:
            message = event.payload
            if not isinstance(message, NetworkMessage):
                raise ValueError("invalid_network_message_event")
            if self._link(message.source, message.destination) in self._partitions:
                self.dropped.append(message)
            else:
                self.delivered.append(message)
        return self.twin.run({"network_delivery": deliver}, max_events=max_events)
