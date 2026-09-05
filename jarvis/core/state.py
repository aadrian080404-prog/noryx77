"""Transactional JARVIS execution state boundary."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from .contracts import Request


@dataclass
class JarvisState:
    """Ephemeral execution state; raw request text is never persisted by the store."""

    request_id: str
    principal_id: str
    plan_id: str = ""
    completed_steps: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    status: str = "initialized"


@dataclass(frozen=True)
class StateSnapshot:
    request_id: str
    principal_id: str
    state: JarvisState
    sequence: int


class JarvisStateStore:
    """Bounded, isolated state store with immutable snapshots at the API boundary."""

    VALID_STATUSES = {"initialized", "planned", "executing", "completed", "rejected"}

    def __init__(self, max_snapshots: int = 10_000) -> None:
        if isinstance(max_snapshots, bool) or not isinstance(max_snapshots, int) or max_snapshots < 1:
            raise ValueError("max_snapshots must be a positive integer")
        self.max_snapshots = max_snapshots
        self._snapshots: dict[str, StateSnapshot] = {}
        self._sequence = 0
        self._lock = RLock()

    def create(self, request: Request) -> JarvisState:
        if not isinstance(request, Request):
            raise TypeError("request_required")
        return JarvisState(request.request_id, request.principal_id)

    def commit(self, state: JarvisState) -> StateSnapshot:
        if not isinstance(state, JarvisState):
            raise TypeError("state_required")
        if not state.request_id.strip() or not state.principal_id.strip():
            raise ValueError("state_identity_required")
        if state.status not in self.VALID_STATUSES:
            raise ValueError("invalid_state_status")
        if not isinstance(state.completed_steps, list) or not isinstance(state.results, list):
            raise ValueError("invalid_state_collections")
        with self._lock:
            if state.request_id not in self._snapshots and len(self._snapshots) >= self.max_snapshots:
                raise MemoryError("state_capacity_exceeded")
            self._sequence += 1
            snapshot = StateSnapshot(
                state.request_id,
                state.principal_id,
                deepcopy(state),
                self._sequence,
            )
            self._snapshots[state.request_id] = snapshot
            return deepcopy(snapshot)

    def get(self, request_id: str, *, principal_id: str | None = None) -> StateSnapshot | None:
        if not isinstance(request_id, str) or not request_id.strip():
            return None
        with self._lock:
            snapshot = self._snapshots.get(request_id)
            if snapshot is None:
                return None
            if principal_id is not None and snapshot.principal_id != principal_id:
                return None
            return deepcopy(snapshot)

    def __len__(self) -> int:
        with self._lock:
            return len(self._snapshots)
