from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from threading import RLock
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .state_journal import StateJournal


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
    """Immutable evidence of one verified state commit and its execution principal."""

    execution_id: str
    task_id: str
    state: NORYXState
    verification_stage: str
    sequence: int
    principal_id: str
    principal_key_fingerprint: str


class StateStore:
    """Transactional state boundary with optional durable journal recovery."""

    MAX_EXECUTION_ID_BYTES = 256
    MAX_TASK_ID_BYTES = 256
    MAX_PRINCIPAL_ID_BYTES = 256
    MAX_DIGEST_LENGTH = 64

    def __init__(self, max_commits: int = 10_000, *, journal: StateJournal | None = None):
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits must be a positive integer")
        self.max_commits = max_commits
        self._journal = journal
        self._commits: dict[str, StateCommit] = {}
        self._sequence = 0
        self._lock = RLock()
        if journal is not None:
            recovered = journal.recover()
            if len(recovered) > max_commits:
                raise MemoryError("journal_exceeds_state_capacity")
            self._commits = deepcopy(recovered)
            self._sequence = max((commit.sequence for commit in recovered.values()), default=0)

    @property
    def version(self) -> int:
        with self._lock:
            return self._sequence

    @staticmethod
    def _valid_id(value: str, max_bytes: int) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= max_bytes

    @classmethod
    def _valid_digest(cls, value: str) -> bool:
        return isinstance(value, str) and len(value) == cls.MAX_DIGEST_LENGTH and all(char in "0123456789abcdef" for char in value)

    @classmethod
    def _valid_fingerprint(cls, value: str) -> bool:
        return cls._valid_digest(value)

    def commit(self, state: NORYXState, *, execution_id: str, task_id: str,
               verification_valid: bool, verification_stage: str,
               principal_id: str, principal_key_fingerprint: str | None = None) -> StateCommit:
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
        if not self._valid_digest(state.input_digest):
            raise ValueError("invalid_input_digest")
        if state.user_input:
            raise PermissionError("raw_user_input_must_not_be_committed")
        if not isinstance(state.confidence, (int, float)) or isinstance(state.confidence, bool):
            raise ValueError("invalid_confidence")
        if not isfinite(float(state.confidence)) or not 0.0 <= float(state.confidence) <= 1.0:
            raise ValueError("invalid_confidence")
        if not isinstance(state.verification_results, list):
            raise ValueError("invalid_verification_results")
        if not self._valid_id(principal_id, self.MAX_PRINCIPAL_ID_BYTES):
            raise ValueError("invalid_principal_id")
        if principal_key_fingerprint is None:
            raise PermissionError("complete_identity_binding_required")
        if not self._valid_fingerprint(principal_key_fingerprint):
            raise ValueError("invalid_principal_key_fingerprint")
        with self._lock:
            if execution_id in self._commits:
                raise PermissionError("execution_already_committed")
            if len(self._commits) >= self.max_commits:
                raise MemoryError("state_capacity_exceeded")
            sequence = self._sequence + 1
            snapshot = deepcopy(state)
            snapshot.status = "committed"
            commit = StateCommit(execution_id, task_id, snapshot, verification_stage, sequence, principal_id, principal_key_fingerprint)
            if self._journal is not None:
                self._journal.append(commit)
            self._commits[execution_id] = commit
            self._sequence = sequence
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
