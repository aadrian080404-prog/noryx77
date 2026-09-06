import hashlib

import pytest

from core.state import NORYXState, StateStore


def _state():
    return NORYXState(
        input_digest=hashlib.sha256(b"input").hexdigest(),
        goal="test",
        final_answer="verified",
        verification_results=[{"stage": "runtime_result", "valid": True}],
        confidence=1.0,
    )


def test_state_store_rejects_duplicate_execution_commit():
    store = StateStore()
    first = store.commit(
        _state(),
        execution_id="execution-1",
        task_id="task-1",
        verification_valid=True,
        verification_stage="runtime_result",
    )

    with pytest.raises(PermissionError, match="execution_already_committed"):
        store.commit(
            _state(),
            execution_id="execution-1",
            task_id="task-1",
            verification_valid=True,
            verification_stage="runtime_result",
        )

    assert store.version == first.sequence == 1
    assert len(store) == 1
