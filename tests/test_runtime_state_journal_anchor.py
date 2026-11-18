import hashlib

import pytest

from core.journal_integrity import InMemoryMonotonicAnchor, JournalAuthenticator
from core.runtime import NORYXRuntime
from core.state import NORYXState


def _authenticator():
    return JournalAuthenticator(b"runtime-state-journal-key-material-32-bytes!!", key_id="runtime-key-v1")


def _state():
    return NORYXState(
        input_digest=hashlib.sha256(b"runtime-state-input").hexdigest(),
        goal="durable verified state",
        confidence=0.95,
        verification_results=[{"stage": "runtime_result", "valid": True}],
    )


def test_runtime_commits_state_only_after_external_anchor_advances(tmp_path):
    path = str(tmp_path / "runtime-state.sqlite3")
    authenticator = _authenticator()
    anchor = InMemoryMonotonicAnchor()
    runtime = NORYXRuntime(
        state_journal_path=path,
        state_journal_authenticator=authenticator,
        state_journal_anchor=anchor,
    )
    commit = runtime.state.commit(
        _state(),
        execution_id="runtime-execution-1",
        task_id="runtime-task-1",
        verification_valid=True,
        verification_stage="runtime_result",
        principal_id="principal-1",
        principal_key_fingerprint="a" * 64,
    )
    assert commit.sequence == 1
    assert anchor.read().sequence == 1
    runtime.state_journal.close()

    recovered = NORYXRuntime(
        state_journal_path=path,
        state_journal_authenticator=authenticator,
        state_journal_anchor=anchor,
    )
    assert recovered.state.version == 1
    assert recovered.state.get("runtime-execution-1").sequence == 1
    recovered.state_journal.close()


def test_runtime_rejects_anchor_without_authenticated_state_journal(tmp_path):
    with pytest.raises(TypeError, match="authenticated_state_journal_anchor_required"):
        NORYXRuntime(
            state_journal_path=str(tmp_path / "invalid-state.sqlite3"),
            state_journal_anchor=InMemoryMonotonicAnchor(),
        )
