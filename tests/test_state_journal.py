import hashlib
import sqlite3

import pytest

from core.state import NORYXState, StateStore
from core.state_journal import StateJournal

TEST_KEY = b"noryx7-test-integrity-key-material-32-bytes"


def make_state():
    return NORYXState(
        input_digest=hashlib.sha256(b"input").hexdigest(),
        goal="verified goal",
        confidence=0.9,
        verification_results=[{"stage": "runtime_result", "valid": True}],
    )


def test_state_store_recovers_durable_commit(tmp_path):
    path = str(tmp_path / "state.db")
    journal = StateJournal(path, integrity_key=TEST_KEY, key_id="test-key")
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



def test_journal_rejects_wrong_external_key(tmp_path):
    path = str(tmp_path / "state.db")
    journal = StateJournal(path, integrity_key=TEST_KEY, key_id="test-key")
    StateStore(journal=journal).commit(
        make_state(), execution_id="exec-key", task_id="task-key",
        verification_valid=True, verification_stage="runtime_result",
        principal_id="principal-key", principal_key_fingerprint="d" * 64,
    )
    journal.close()
    wrong = StateJournal(path, integrity_key=b"another-test-integrity-key-material-32-bytes", key_id="test-key")
    with pytest.raises(RuntimeError, match="state_journal_integrity_failure"):
        wrong.recover()
    wrong.close()


def test_journal_refuses_legacy_unkeyed_schema_without_migration(tmp_path):
    path = str(tmp_path / "legacy.db")
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE state_commits (execution_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, "
        "state_json TEXT NOT NULL, verification_stage TEXT NOT NULL, sequence INTEGER NOT NULL UNIQUE, "
        "principal_id TEXT NOT NULL, principal_key_fingerprint TEXT NOT NULL, "
        "record_digest TEXT NOT NULL, schema_version INTEGER NOT NULL)"
    )
    db.close()
    with pytest.raises(RuntimeError, match="legacy_unkeyed_journal_requires_explicit_migration"):
        StateJournal(path, integrity_key=TEST_KEY, key_id="test-key")


def test_journal_requires_strong_external_key(tmp_path):
    with pytest.raises(ValueError, match="journal_integrity_key_too_short"):
        StateJournal(str(tmp_path / "short.db"), integrity_key=b"short", key_id="test-key")
