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
        self.drop_reasons: list[tuple[NetworkMessage, str]] = []
        self._node_up: dict[str, bool] = {}

    @staticmethod
    def _link(source: str, destination: str) -> frozenset[str]:
        if (not isinstance(source, str) or not source.strip()
                or not isinstance(destination, str) or not destination.strip()
                or source == destination):
            raise ValueError("distinct_network_endpoints_required")
        return frozenset((source, destination))

    def crash_at(self, node_id: str, at: int) -> TwinEvent:
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id_required")
        return self.twin.schedule(at, "node_crash", node_id)

    def restart_at(self, node_id: str, at: int) -> TwinEvent:
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id_required")
        return self.twin.schedule(at, "node_restart", node_id)

    def partition(self, source: str, destination: str) -> None:
        self._partitions.add(self._link(source, destination))

    def heal(self, source: str, destination: str) -> None:
        self._partitions.discard(self._link(source, destination))

    def partition_at(self, source: str, destination: str, at: int) -> TwinEvent:
        link = self._link(source, destination)
        return self.twin.schedule(at, "network_partition", link)

    def heal_at(self, source: str, destination: str, at: int) -> TwinEvent:
        link = self._link(source, destination)
        return self.twin.schedule(at, "network_heal", link)

    def send(self, message_id: str, source: str, destination: str,
             payload: Any, delay: int = 0, *, copies: int = 1) -> TwinEvent:
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError("message_id_required")
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ValueError("network_delay_must_be_nonnegative_integer")
        self._link(source, destination)
        if isinstance(copies, bool) or not isinstance(copies, int) or not 1 <= copies <= 16:
            raise ValueError("network_copies_must_be_between_1_and_16")
        message = NetworkMessage(message_id, source, destination, payload)
        first = None
        for _ in range(copies):
            event = self.twin.schedule(self.twin.now + delay, "network_delivery", message)
            if first is None:
                first = event
        return first

    def run(self, max_events: int = 10000) -> tuple[TwinEvent, ...]:
        def partition(event: TwinEvent, _sim: DeterministicTwin) -> None:
            if not isinstance(event.payload, frozenset) or len(event.payload) != 2:
                raise ValueError("invalid_network_partition_event")
            self._partitions.add(event.payload)

        def heal(event: TwinEvent, _sim: DeterministicTwin) -> None:
            if not isinstance(event.payload, frozenset) or len(event.payload) != 2:
                raise ValueError("invalid_network_heal_event")
            self._partitions.discard(event.payload)

        def node_crash(event: TwinEvent, _sim: DeterministicTwin) -> None:
            if not isinstance(event.payload, str) or not event.payload.strip():
                raise ValueError("invalid_node_crash_event")
            self._node_up[event.payload] = False

        def node_restart(event: TwinEvent, _sim: DeterministicTwin) -> None:
            if not isinstance(event.payload, str) or not event.payload.strip():
                raise ValueError("invalid_node_restart_event")
            self._node_up[event.payload] = True

        def deliver(event: TwinEvent, _sim: DeterministicTwin) -> None:
            message = event.payload
            if not isinstance(message, NetworkMessage):
                raise ValueError("invalid_network_message_event")
            if self._link(message.source, message.destination) in self._partitions:
                self.dropped.append(message)
                self.drop_reasons.append((message, "PARTITION"))
            elif not self._node_up.get(message.source, True) or not self._node_up.get(message.destination, True):
                self.dropped.append(message)
                self.drop_reasons.append((message, "NODE_UNAVAILABLE"))
            else:
                self.delivered.append(message)

        return self.twin.run({
            "network_partition": partition,
            "network_heal": heal,
            "node_crash": node_crash,
            "node_restart": node_restart,
            "network_delivery": deliver,
        }, max_events=max_events)
