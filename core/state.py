from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NORYXState:
    """Bounded internal state; unverified data never becomes committed state."""

    user_input: str = ""
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
    """Small transactional state boundary with monotonic per-execution commits."""

    MAX_EXECUTION_ID_BYTES = 256
    MAX_TASK_ID_BYTES = 256

    def __init__(self, max_commits: int = 10_000):
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits must be a positive integer")
        self.max_commits = max_commits
        self._commits: dict[str, StateCommit] = {}
        self._sequence = 0

    @staticmethod
    def _valid_id(value: str, max_bytes: int) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= max_bytes

    def commit(
        self,
        state: NORYXState,
        *,
        execution_id: str,
        task_id: str,
        verification_valid: bool,
        verification_stage: str,
    ) -> StateCommit:
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
        if len(self._commits) >= self.max_commits and execution_id not in self._commits:
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
        commit = self._commits.get(execution_id)
        return deepcopy(commit) if commit is not None else None

    def __len__(self) -> int:
        return len(self._commits)
