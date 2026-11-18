import hashlib
import sqlite3

import pytest

from core.state import NORYXState, StateCommit, StateStore
from core.state_journal import StateJournal
from core.journal_integrity import InMemoryMonotonicAnchor, JournalAuthenticator


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


def _authenticator():
    return JournalAuthenticator(b"noryx7-test-journal-key-material-32-bytes!!", key_id="test-key-v1")


def test_state_journal_hmac_chain_and_external_anchor(tmp_path):
    path = str(tmp_path / "anchored-state.db")
    authenticator = _authenticator()
    anchor = InMemoryMonotonicAnchor()
    journal = StateJournal(path, authenticator=authenticator)
    journal.append(_manual_commit("anchored-1", 1))
    journal.append(_manual_commit("anchored-2", 2))

    head = journal.verify_and_advance_anchor(anchor)
    assert head.sequence == 2
    assert anchor.read() == head
    journal.close()

    reopened = StateJournal(path, authenticator=authenticator)
    assert len(reopened.recover()) == 2
    assert reopened.verify_and_advance_anchor(anchor) == head
    reopened.close()


def test_state_journal_migrates_legacy_records_to_authenticated_chain(tmp_path):
    path = str(tmp_path / "legacy-state.db")
    legacy = StateJournal(path)
    legacy.append(_manual_commit("legacy-1", 1))
    legacy.append(_manual_commit("legacy-2", 2))
    legacy.close()

    authenticated = StateJournal(path, authenticator=_authenticator())
    assert len(authenticated.recover()) == 2
    assert authenticated.verify_and_advance_anchor(InMemoryMonotonicAnchor()).sequence == 2
    authenticated.close()


def test_state_journal_external_anchor_detects_database_rollback(tmp_path):
    path = str(tmp_path / "rollback-state.db")
    authenticator = _authenticator()
    anchor = InMemoryMonotonicAnchor()
    journal = StateJournal(path, authenticator=authenticator)
    journal.append(_manual_commit("rollback-1", 1))
    journal.append(_manual_commit("rollback-2", 2))
    anchored_head = journal.verify_and_advance_anchor(anchor)
    journal.close()

    connection = sqlite3.connect(path)
    connection.execute("DELETE FROM state_commits WHERE sequence=2")
    connection.execute("DELETE FROM state_journal_proofs WHERE sequence=2")
    connection.commit()
    connection.close()

    rolled_back = StateJournal(path, authenticator=authenticator)
    with pytest.raises(RuntimeError, match="state_journal_rollback_detected"):
        rolled_back.verify_and_advance_anchor(anchor)
    rolled_back.close()


def test_state_journal_rejects_modified_chain_proof(tmp_path):
    path = str(tmp_path / "tampered-proof.db")
    journal = StateJournal(path, authenticator=_authenticator())
    journal.append(_manual_commit("proof-1", 1))
    journal.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE state_journal_proofs SET mac=? WHERE sequence=1", ("f" * 64,)
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="state_journal_authentication_failure"):
        StateJournal(path, authenticator=_authenticator())


def test_state_journal_refuses_authenticated_records_without_key(tmp_path):
    path = str(tmp_path / "missing-key.db")
    journal = StateJournal(path, authenticator=_authenticator())
    journal.append(_manual_commit("requires-key", 1))
    journal.close()

    reopened = StateJournal(path)
    with pytest.raises(RuntimeError, match="state_journal_authenticator_required"):
        reopened.recover()
    reopened.close()
