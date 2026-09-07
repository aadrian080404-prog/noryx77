"""Transactional state boundary for standalone JARVIS.

Only verified execution results may cross into persistent state. Raw request text
is never stored; callers retain only bounded digests and execution metadata.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from threading import RLock
from typing import Any

MAX_ID_BYTES = 256
MAX_DIGEST_LENGTH = 64
MAX_RESULTS = 256
VALID_STATUSES = {"initialized", "completed", "verified", "committed"}

@dataclass
class JarvisState:
    execution_id: str
    request_id: str
    principal_id: str
    request_digest: str
    completed_steps: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    status: str = "initialized"

@dataclass(frozen=True)
class StateCommit:
    execution_id: str
    request_id: str
    state: JarvisState
    sequence: int
    principal_id: str

@dataclass(frozen=True)
class ExecutionReservation:
    execution_id: str
    request_id: str
    principal_id: str

def _valid_id(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= MAX_ID_BYTES

class JarvisStateStore:
    """Thread-safe, bounded, verified-only JARVIS state store with pre-execution reservation."""
    def __init__(self, max_commits: int = 10_000) -> None:
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1: raise ValueError("invalid_max_commits")
        self._max_commits = max_commits; self._commits: dict[str, StateCommit] = {}; self._reservations: dict[str, ExecutionReservation] = {}; self._sequence = 0; self._lock = RLock()

    @staticmethod
    def digest_request(text: str) -> str:
        if not isinstance(text, str) or not text.strip(): raise ValueError("request_text_required")
        return sha256(text.encode("utf-8")).hexdigest()

    def create(self, request) -> JarvisState:
        from .contracts import Request
        if not isinstance(request, Request): raise TypeError("request_required")
        return JarvisState(request.request_id, request.request_id, request.principal_id, self.digest_request(request.text))

    def reserve(self, *, execution_id: str, request_id: str, principal_id: str) -> ExecutionReservation:
        if not _valid_id(execution_id) or not _valid_id(request_id) or not _valid_id(principal_id): raise ValueError("invalid_identity")
        with self._lock:
            if execution_id in self._commits: raise PermissionError("execution_already_committed")
            existing = self._reservations.get(execution_id)
            if existing is not None:
                if existing.request_id != request_id or existing.principal_id != principal_id: raise PermissionError("execution_reservation_mismatch")
                raise PermissionError("execution_already_reserved")
            reservation = ExecutionReservation(execution_id, request_id, principal_id); self._reservations[execution_id] = reservation; return reservation

    def commit(self, state: JarvisState, *, verified_results: bool = True, execution_id: str | None = None, request_id: str | None = None, principal_id: str | None = None) -> StateCommit:
        if not isinstance(state, JarvisState): raise TypeError("state_required")
        execution_id = state.execution_id if execution_id is None else execution_id; request_id = state.request_id if request_id is None else request_id; principal_id = state.principal_id if principal_id is None else principal_id
        if not _valid_id(execution_id) or not _valid_id(request_id) or not _valid_id(principal_id): raise ValueError("invalid_identity")
        if state.execution_id != execution_id or state.request_id != request_id: raise ValueError("state_identity_mismatch")
        if state.principal_id != principal_id: raise ValueError("state_principal_mismatch")
        if verified_results is not True: raise PermissionError("verified_results_required")
        if state.status not in VALID_STATUSES: raise ValueError("invalid_state_status")
        if not isinstance(state.request_digest, str) or len(state.request_digest) != MAX_DIGEST_LENGTH: raise ValueError("invalid_request_digest")
        if not isinstance(state.completed_steps, list) or len(state.completed_steps) > MAX_RESULTS: raise ValueError("state_capacity_exceeded")
        if not isinstance(state.results, list) or len(state.results) > MAX_RESULTS: raise ValueError("result_capacity_exceeded")
        if any(not _valid_id(step) for step in state.completed_steps): raise ValueError("invalid_step_id")
        with self._lock:
            if execution_id in self._commits: raise PermissionError("execution_already_committed")
            reservation = self._reservations.get(execution_id)
            if reservation is not None and (reservation.request_id != request_id or reservation.principal_id != principal_id): raise PermissionError("execution_reservation_mismatch")
            if len(self._commits) >= self._max_commits: raise MemoryError("state_capacity_exceeded")
            self._sequence += 1; snapshot = deepcopy(state); snapshot.status = "committed"; commit = StateCommit(execution_id, request_id, snapshot, self._sequence, principal_id)
            self._commits[execution_id] = commit; self._reservations.pop(execution_id, None); return deepcopy(commit)

    def get(self, execution_id: str, *, principal_id: str | None = None) -> StateCommit | None:
        if not _valid_id(execution_id): return None
        if principal_id is not None and not _valid_id(principal_id): return None
        with self._lock:
            value = self._commits.get(execution_id)
            if value is None or (principal_id is not None and value.principal_id != principal_id): return None
            return deepcopy(value)

    def reservation(self, execution_id: str) -> ExecutionReservation | None:
        if not _valid_id(execution_id): return None
        with self._lock: return self._reservations.get(execution_id)

    def __len__(self) -> int:
        with self._lock: return len(self._commits)
