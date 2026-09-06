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


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= MAX_ID_BYTES


class JarvisStateStore:
    """Thread-safe, bounded, verified-only JARVIS state store."""

    def __init__(self, max_commits: int = 10_000) -> None:
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("invalid_max_commits")
        self._max_commits = max_commits
        self._commits: dict[str, StateCommit] = {}
        self._sequence = 0
        self._lock = RLock()

    @staticmethod
    def digest_request(text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("request_text_required")
        return sha256(text.encode("utf-8")).hexdigest()

    def commit(
        self,
        state: JarvisState,
        *,
        verified_results: bool,
        execution_id: str,
        request_id: str,
        principal_id: str,
    ) -> StateCommit:
        if not isinstance(state, JarvisState):
            raise TypeError("state_required")
        if not _valid_id(execution_id) or not _valid_id(request_id) or not _valid_id(principal_id):
            raise ValueError("invalid_identity")
        if state.execution_id != execution_id or state.request_id != request_id:
            raise ValueError("state_identity_mismatch")
        if state.principal_id != principal_id:
            raise ValueError("state_principal_mismatch")
        if verified_results is not True:
            raise PermissionError("verified_results_required")
        if not isinstance(state.request_digest, str) or len(state.request_digest) != MAX_DIGEST_LENGTH:
            raise ValueError("invalid_request_digest")
        if not isinstance(state.completed_steps, list) or len(state.completed_steps) > MAX_RESULTS:
            raise ValueError("state_capacity_exceeded")
        if not isinstance(state.results, list) or len(state.results) > MAX_RESULTS:
            raise ValueError("result_capacity_exceeded")
        if any(not _valid_id(step) for step in state.completed_steps):
            raise ValueError("invalid_step_id")
        with self._lock:
            if execution_id in self._commits:
                raise PermissionError("execution_already_committed")
            if len(self._commits) >= self._max_commits:
                raise MemoryError("state_capacity_exceeded")
            self._sequence += 1
            snapshot = deepcopy(state)
            snapshot.status = "committed"
            commit = StateCommit(execution_id, request_id, snapshot, self._sequence, principal_id)
            self._commits[execution_id] = commit
            return deepcopy(commit)

    def get(self, execution_id: str) -> StateCommit | None:
        if not _valid_id(execution_id):
            return None
        with self._lock:
            value = self._commits.get(execution_id)
            return deepcopy(value) if value is not None else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._commits)
