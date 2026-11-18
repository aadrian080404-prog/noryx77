from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import stat

import pytest

from core.state import NORYXState, StateCommit, StateStore
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



def _manual_commit(execution_id, sequence):
    return StateCommit(
        execution_id=execution_id,
        task_id=f"task-{execution_id}",
        state=make_state(),
        verification_stage="runtime_result",
        sequence=sequence,
        principal_id="principal-1",
        principal_key_fingerprint="a" * 64,
    )


def test_state_journal_serializes_capacity_and_sequence_across_instances(tmp_path):
    path = str(tmp_path / "shared-state.db")
    first = StateJournal(path, max_commits=1)
    second = StateJournal(path, max_commits=1)
    commits = (
        (first, _manual_commit("exec-first", 1)),
        (second, _manual_commit("exec-second", 2)),
    )

    def append_one(item):
        journal, commit = item
        try:
            journal.append(commit)
            return "committed"
        except (MemoryError, RuntimeError):
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(append_one, commits))

    assert results.count("committed") == 1
    assert results.count("rejected") == 1
    recovered = first.recover()
    assert len(recovered) == 1
    assert next(iter(recovered.values())).sequence == 1
    first.close()
    second.close()


def test_state_journal_rejects_capacity_configuration_mismatch(tmp_path):
    path = str(tmp_path / "state-config.db")
    journal = StateJournal(path, max_commits=2)
    journal.close()
    with pytest.raises(ValueError, match="state_journal_configuration_mismatch"):
        StateJournal(path, max_commits=3)


def test_state_journal_requires_persistent_storage():
    with pytest.raises(ValueError, match="persistent_journal_path_required"):
        StateJournal(":memory:")


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permission semantics required")
def test_state_journal_restricts_database_file_permissions(tmp_path):
    path = tmp_path / "private-state.db"
    journal = StateJournal(str(path))
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        journal.close()



def test_state_journal_rejects_boolean_sequence_numbers(tmp_path):
    journal = StateJournal(str(tmp_path / "invalid-sequence.db"))
    with pytest.raises(ValueError, match="invalid_state_commit_sequence"):
        journal.append(_manual_commit("exec-bool", True))
    assert journal.recover() == {}
    journal.close()
