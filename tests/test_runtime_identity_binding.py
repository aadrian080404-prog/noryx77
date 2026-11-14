import hashlib

import pytest

from core.identity import AgentIdentity, AgentIdentityAuthority
from core.state import NORYXState, StateStore


def _state():
    return NORYXState(
        input_digest=hashlib.sha256(b"input").hexdigest(),
        goal="test",
        final_answer="verified",
        verification_results=[{"stage": "runtime_result", "valid": True}],
        confidence=1.0,
    )


def test_state_commit_rejects_partial_identity_binding():
    store = StateStore()
    with pytest.raises(PermissionError, match="complete_identity_binding_required"):
        store.commit(
            _state(), execution_id="execution-1", task_id="task-1",
            principal_id="deterministic", verification_valid=True,
            verification_stage="runtime_result",
        )


def test_state_commit_rejects_malformed_identity_fingerprint():
    store = StateStore()
    with pytest.raises(ValueError, match="invalid_principal_key_fingerprint"):
        store.commit(
            _state(), execution_id="execution-1", task_id="task-1",
            principal_id="deterministic", principal_key_fingerprint="not-a-digest",
            verification_valid=True, verification_stage="runtime_result",
        )


def test_identity_fingerprint_is_bound_to_the_registered_public_key():
    identity, _ = AgentIdentityAuthority.generate("deterministic")
    assert identity.is_well_formed()
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    store = StateStore()
    commit = store.commit(
        _state(), execution_id="execution-1", task_id="task-1",
        principal_id=identity.agent_id, principal_key_fingerprint=fingerprint,
        verification_valid=True, verification_stage="runtime_result",
    )
    assert commit.principal_id == "deterministic"
    assert commit.principal_key_fingerprint == fingerprint


def test_identity_swapping_changes_fingerprint_and_cannot_match_original():
    first, _ = AgentIdentityAuthority.generate("deterministic")
    second, _ = AgentIdentityAuthority.generate("deterministic")
    assert first.public_key != second.public_key
    first_fp = hashlib.sha256(first.public_key).hexdigest()
    second_fp = hashlib.sha256(second.public_key).hexdigest()
    assert first_fp != second_fp
