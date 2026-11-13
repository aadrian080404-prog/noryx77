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

    reopened = StateJournal(path, integrity_key=TEST_KEY, key_id="test-key")
    recovered = StateStore(journal=reopened)
    assert recovered.version == commit.sequence
    assert recovered.get("exec-1") == commit
    reopened.close()


def test_journal_rejects_tampered_record(tmp_path):
    path = str(tmp_path / "state.db")
    journal = StateJournal(path, integrity_key=TEST_KEY, key_id="test-key")
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
    journal = StateJournal(str(tmp_path / "state.db"), integrity_key=TEST_KEY, key_id="test-key")
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


from core.journal_integrity import AnchorSnapshot, InMemoryMonotonicAnchor
from core.journal_integrity import ZERO_MAC


def _anchored_journal(path, anchor, **kwargs):
    return StateJournal(
        str(path),
        integrity_key=TEST_KEY,
        key_id="test-key",
        monotonic_anchor=anchor,
        require_external_anchor=True,
        **kwargs,
    )


def test_external_anchor_tracks_durable_journal_head(tmp_path):
    anchor = InMemoryMonotonicAnchor()
    path = tmp_path / "anchored.db"
    journal = _anchored_journal(path, anchor)
    store = StateStore(journal=journal)
    commit = store.commit(
        make_state(), execution_id="anchor-1", task_id="task-anchor-1",
        verification_valid=True, verification_stage="runtime_result",
        principal_id="principal-anchor-1", principal_key_fingerprint="e" * 64,
    )
    assert anchor.read().sequence == commit.sequence
    assert anchor.read().mac != ZERO_MAC
    assert journal.rollback_protected
    journal.close()


def test_external_anchor_detects_database_rollback(tmp_path):
    anchor = InMemoryMonotonicAnchor()
    path = tmp_path / "rollback.db"
    journal = _anchored_journal(path, anchor)
    StateStore(journal=journal).commit(
        make_state(), execution_id="anchor-rollback", task_id="task-rollback",
        verification_valid=True, verification_stage="runtime_result",
        principal_id="principal-rollback", principal_key_fingerprint="f" * 64,
    )
    journal._db.execute("DELETE FROM state_commits")
    journal.close()

    reopened = _anchored_journal(path, anchor)
    with pytest.raises(RuntimeError, match="state_journal_anchor_mismatch"):
        reopened.recover()
    reopened.close()


def test_external_anchor_repairs_single_commit_crash_gap(tmp_path):
    class FailFirstCAS:
        def __init__(self):
            self.inner = InMemoryMonotonicAnchor()
            self.failed = False

        def read(self):
            return self.inner.read()

        def compare_and_swap(self, expected, replacement):
            if not self.failed:
                self.failed = True
                return False
            return self.inner.compare_and_swap(expected, replacement)

    anchor = FailFirstCAS()
    path = tmp_path / "crash-gap.db"
    journal = _anchored_journal(path, anchor)
    store = StateStore(journal=journal)
    with pytest.raises(RuntimeError, match="state_journal_anchor_update_failed"):
        store.commit(
            make_state(), execution_id="anchor-crash", task_id="task-crash",
            verification_valid=True, verification_stage="runtime_result",
            principal_id="principal-crash", principal_key_fingerprint="1" * 64,
        )
    # The DB commit happened, but the caller did not publish it in memory.
    assert store.version == 0
    journal.close()

    reopened = _anchored_journal(path, anchor)
    recovered = StateStore(journal=reopened)
    assert recovered.version == 1
    assert recovered.get("anchor-crash") is not None
    assert anchor.read().sequence == 1
    reopened.close()


def test_external_anchor_rejects_missing_anchor_when_required(tmp_path):
    with pytest.raises(ValueError, match="external_monotonic_anchor_required"):
        StateJournal(
            str(tmp_path / "missing-anchor.db"),
            integrity_key=TEST_KEY,
            key_id="test-key",
            require_external_anchor=True,
        )


def test_external_anchor_rejects_same_sequence_divergent_mac(tmp_path):
    class DivergentAnchor:
        def read(self):
            return AnchorSnapshot(0, "a" * 64)

        def compare_and_swap(self, expected, replacement):
            return False

    journal = _anchored_journal(tmp_path / "divergent.db", DivergentAnchor())
    with pytest.raises(RuntimeError, match="state_journal_anchor_mismatch"):
        journal.recover()
    journal.close()
