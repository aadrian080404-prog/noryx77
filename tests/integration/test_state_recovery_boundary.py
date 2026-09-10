from __future__ import annotations

import hashlib
import sqlite3

import pytest

from core.state import NORYXState, StateStore
from core.state_journal import StateJournal


def _state(value: str) -> NORYXState:
    return NORYXState(
        input_digest=hashlib.sha256(value.encode()).hexdigest(),
        goal="recovery-test",
        verification_results=[{"stage": "runtime_result", "valid": True}],
        confidence=1.0,
        final_answer="verified-result",
        status="verified",
    )


def test_state_store_survives_runtime_restart(tmp_path):
    path = str(tmp_path / "state.sqlite3")

    journal = StateJournal(path)
    store = StateStore(journal=journal)
    first = store.commit(
        _state("first"),
        execution_id="exec-001",
        task_id="task-001",
        verification_valid=True,
        verification_stage="runtime_result",
        principal_id="principal-001",
        principal_key_fingerprint="a" * 64,
    )
    assert first.sequence == 1
    assert store.get("exec-001") is not None
    journal.close()

    restarted_journal = StateJournal(path)
    restarted_store = StateStore(journal=restarted_journal)
    recovered = restarted_store.get("exec-001")
    assert recovered is not None
    assert recovered.sequence == 1
    assert recovered.principal_id == "principal-001"
    assert recovered.state.final_answer == "verified-result"
    restarted_journal.close()


def test_state_store_recovery_rejects_journal_sequence_gap(tmp_path):
    path = str(tmp_path / "state.sqlite3")
    journal = StateJournal(path)
    store = StateStore(journal=journal)
    store.commit(
        _state("first"),
        execution_id="exec-001",
        task_id="task-001",
        verification_valid=True,
        verification_stage="runtime_result",
        principal_id="principal-001",
        principal_key_fingerprint="a" * 64,
    )
    journal.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE state_commits SET sequence=2 WHERE execution_id='exec-001'")
    db.commit()
    db.close()

    corrupted = StateJournal(path)
    with pytest.raises(RuntimeError, match="state_journal_sequence_gap"):
        StateStore(journal=corrupted)
    corrupted.close()


def test_state_store_does_not_commit_raw_input(tmp_path):
    path = str(tmp_path / "state.sqlite3")
    journal = StateJournal(path)
    store = StateStore(journal=journal)
    state = _state("raw-input")
    state.user_input = "secret raw input"
    with pytest.raises(PermissionError, match="raw_user_input_must_not_be_committed"):
        store.commit(
            state,
            execution_id="exec-raw",
            task_id="task-raw",
            verification_valid=True,
            verification_stage="runtime_result",
            principal_id="principal-raw",
            principal_key_fingerprint="b" * 64,
        )
    journal.close()
