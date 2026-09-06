import hashlib

import pytest

from core.state import NORYXState, StateStore
from core.state_journal import StateJournal


def make_state():
    return NORYXState(
        input_digest=hashlib.sha256(b"input").hexdigest(),
        goal="verified goal",
        confidence=0.9,
        verification_results=[{"stage": "runtime_result", "valid": True}],
    )


def test_state_store_recovers_durable_commit(tmp_path):
    path = str(tmp_path / "state.db")
    journal = StateJournal(path)
    store = StateStore(journal=journal)
    commit = store.commit(
        make_state(), execution_id="exec-1", task_id="task-1",
        verification_valid=True, verification_stage="runtime_result",
        principal_id="principal-1", principal_key_fingerprint="a" * 64,
    )
    journal.close()

    reopened = StateJournal(path)
    recovered = StateStore(journal=reopened)
    assert recovered.version == commit.sequence
    assert recovered.get("exec-1") == commit
    reopened.close()


def test_journal_rejects_tampered_record(tmp_path):
    path = str(tmp_path / "state.db")
    journal = StateJournal(path)
    store = StateStore(journal=journal)
    store.commit(
        make_state(), execution_id="exec-2", task_id="task-2",
        verification_valid=True, verification_stage="runtime_result",
        principal_id="principal-2", principal_key_fingerprint="b" * 64,
    )
    journal._db.execute("UPDATE state_commits SET state_json=? WHERE execution_id=?", ('{"goal":"tampered"}', "exec-2"))
    with pytest.raises(RuntimeError, match="state_journal_integrity_failure"):
        journal.recover()
    journal.close()


def test_failed_durable_append_does_not_publish_in_memory(monkeypatch, tmp_path):
    journal = StateJournal(str(tmp_path / "state.db"))
    store = StateStore(journal=journal)
    monkeypatch.setattr(journal, "append", lambda commit: (_ for _ in ()).throw(OSError("disk failure")))
    with pytest.raises(OSError, match="disk failure"):
        store.commit(
            make_state(), execution_id="exec-3", task_id="task-3",
            verification_valid=True, verification_stage="runtime_result",
            principal_id="principal-3", principal_key_fingerprint="c" * 64,
        )
    assert len(store) == 0
    assert store.version == 0
    journal.close()
