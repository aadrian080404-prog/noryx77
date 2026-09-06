from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from threading import RLock
from typing import Any


@dataclass
class NORYXState:
    """Bounded internal state; persistent state contains references, not raw user content."""

    user_input: str = ""
    input_digest: str = ""
    context: list[str] = field(default_factory=list)
    goal: str = ""
    subtasks: list[str] = field(default_factory=list)
    memory: list[dict[str, Any]] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    selected_models: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    current_action: str = ""
    final_answer: str = ""
    status: str = "initialized"


@dataclass(frozen=True)
class StateCommit:
    """Immutable evidence of one verified state commit."""

    execution_id: str
    task_id: str
    state: NORYXState
    verification_stage: str
    sequence: int


class StateStore:
    """Transactional state boundary with monotonic commits and input-reference hygiene."""

    MAX_EXECUTION_ID_BYTES = 256
    MAX_TASK_ID_BYTES = 256
    MAX_DIGEST_LENGTH = 64

    def __init__(self, max_commits: int = 10_000):
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits must be a positive integer")
        self.max_commits = max_commits
        self._commits: dict[str, StateCommit] = {}
        self._sequence = 0
        self._lock = RLock()

    @property
    def version(self) -> int:
        """Monotonic local state version used as an offline sync base."""
        with self._lock:
            return self._sequence

    @staticmethod
    def _valid_id(value: str, max_bytes: int) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= max_bytes

    def commit(self, state: NORYXState, *, execution_id: str, task_id: str,
               verification_valid: bool, verification_stage: str) -> StateCommit:
        if not isinstance(state, NORYXState):
            raise TypeError("state_required")
        if not self._valid_id(execution_id, self.MAX_EXECUTION_ID_BYTES):
            raise ValueError("invalid_execution_id")
        if not self._valid_id(task_id, self.MAX_TASK_ID_BYTES):
            raise ValueError("invalid_task_id")
        if verification_valid is not True:
            raise PermissionError("verified_commit_required")
        if not isinstance(verification_stage, str) or verification_stage.strip() != "runtime_result":
            raise PermissionError("runtime_verification_required")
        if not isinstance(state.input_digest, str) or len(state.input_digest) != self.MAX_DIGEST_LENGTH:
            raise ValueError("invalid_input_digest")
        if state.user_input:
            raise PermissionError("raw_user_input_must_not_be_committed")
        if not isinstance(state.confidence, (int, float)) or isinstance(state.confidence, bool):
            raise ValueError("invalid_confidence")
        if not isfinite(float(state.confidence)) or not 0.0 <= float(state.confidence) <= 1.0:
            raise ValueError("invalid_confidence")
        if not isinstance(state.verification_results, list):
            raise ValueError("invalid_verification_results")
        with self._lock:
            if execution_id in self._commits:
                raise PermissionError("execution_already_committed")
            if len(self._commits) >= self.max_commits:
                raise MemoryError("state_capacity_exceeded")
            self._sequence += 1
            snapshot = deepcopy(state)
            snapshot.status = "committed"
            commit = StateCommit(execution_id, task_id, snapshot, verification_stage, self._sequence)
            self._commits[execution_id] = commit
            return deepcopy(commit)

    def get(self, execution_id: str) -> StateCommit | None:
        if not self._valid_id(execution_id, self.MAX_EXECUTION_ID_BYTES):
            return None
        with self._lock:
            commit = self._commits.get(execution_id)
            return deepcopy(commit) if commit is not None else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._commits)
