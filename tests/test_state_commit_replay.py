import hashlib

import pytest

from core.state import NORYXState, StateStore


PRINCIPAL_ID = "agent-a"
PRINCIPAL_FINGERPRINT = hashlib.sha256(b"agent-a-public-key").hexdigest()


def _state():
    return NORYXState(
        input_digest=hashlib.sha256(b"input").hexdigest(),
        goal="test",
        final_answer="verified",
        verification_results=[{"stage": "runtime_result", "valid": True}],
        confidence=1.0,
    )


def _commit(store, execution_id="execution-1", task_id="task-1", principal_id=PRINCIPAL_ID, fingerprint=PRINCIPAL_FINGERPRINT):
    return store.commit(
        _state(),
        execution_id=execution_id,
        task_id=task_id,
        verification_valid=True,
        verification_stage="runtime_result",
        principal_id=principal_id,
        principal_key_fingerprint=fingerprint,
    )


def test_state_store_rejects_duplicate_execution_commit():
    store = StateStore()
    first = _commit(store)

    with pytest.raises(PermissionError, match="execution_already_committed"):
        _commit(store)

    assert store.version == first.sequence == 1
    assert len(store) == 1


def test_state_store_rejects_partial_identity_binding():
    store = StateStore()
    with pytest.raises(ValueError, match="invalid_principal_id"):
        _commit(store, execution_id="execution-2", principal_id="")


def test_state_store_rejects_malformed_identity_fingerprint():
    store = StateStore()
    with pytest.raises(ValueError, match="invalid_principal_key_fingerprint"):
        _commit(store, execution_id="execution-3", fingerprint="A" * 64)
