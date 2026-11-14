import hashlib
import sqlite3
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.anchored_state_journal import AnchoredStateJournal
from core.journal_integrity import AnchorSnapshot, InMemoryMonotonicAnchor, ZERO_MAC
from core.remote_witness import RemoteMonotonicAnchor, SignedWitnessReceipt
from core.state import NORYXState, StateCommit
from core.state_journal import StateJournal


KEY = b"anchored-state-journal-test-key-material-32-bytes"


class FakeRemoteWitness:
    def __init__(self):
        self.witness_id = "witness-a"
        self.private_key = Ed25519PrivateKey.generate()
        self.snapshot = AnchorSnapshot(0, ZERO_MAC)
        self.reject_cas = False
        self.wrong_nonce = False

    @property
    def public_key(self):
        return self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def _receipt(self, operation, nonce, accepted):
        actual_nonce = b"x" * 32 if self.wrong_nonce else nonce
        unsigned = SignedWitnessReceipt(
            self.witness_id, operation, actual_nonce, self.snapshot, accepted, b""
        )
        signature = self.private_key.sign(RemoteMonotonicAnchor._message(unsigned))
        return replace(unsigned, signature=signature)

    def read_anchor(self, nonce):
        return self._receipt("read", nonce, True)

    def compare_and_swap_anchor(self, expected, replacement, nonce):
        accepted = not self.reject_cas and self.snapshot == expected
        if accepted:
            self.snapshot = replacement
        return self._receipt("compare_and_swap", nonce, accepted)


def make_commit(sequence, execution_id):
    return StateCommit(
        execution_id=execution_id,
        task_id="task-" + execution_id,
        state=NORYXState(
            input_digest=hashlib.sha256(execution_id.encode()).hexdigest(),
            goal="verified",
            confidence=0.9,
            verification_results=[{"stage": "runtime_result", "valid": True}],
        ),
        verification_stage="runtime_result",
        sequence=sequence,
        principal_id="principal-1",
        principal_key_fingerprint="a" * 64,
    )


def test_remote_witness_verifies_signed_nonce_bound_receipts():
    service = FakeRemoteWitness()
    anchor = RemoteMonotonicAnchor(
        service, witness_id="witness-a", trusted_public_key=service.public_key
    )
    initial = anchor.read()
    next_state = AnchorSnapshot(1, "b" * 64)
    assert anchor.compare_and_swap(initial, next_state)
    assert anchor.read() == next_state
    assert not anchor.compare_and_swap(initial, AnchorSnapshot(1, "c" * 64))


def test_remote_witness_rejects_wrong_nonce_even_with_valid_signature():
    service = FakeRemoteWitness()
    service.wrong_nonce = True
    anchor = RemoteMonotonicAnchor(
        service, witness_id="witness-a", trusted_public_key=service.public_key
    )
    with pytest.raises(RuntimeError, match="nonce_mismatch"):
        anchor.read()


def test_anchored_state_journal_updates_external_head_and_recovers(tmp_path):
    path = str(tmp_path / "state.sqlite")
    anchor = InMemoryMonotonicAnchor()
    journal = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    journal.append(make_commit(1, "exec-1"))
    assert anchor.read().sequence == 1
    journal.close()

    reopened = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    assert reopened.get("exec-1") is not None
    assert reopened.recover()["exec-1"].sequence == 1
    reopened.close()


def test_anchored_journal_reconciles_single_db_commit_crash_gap(tmp_path):
    path = str(tmp_path / "state.sqlite")
    anchor = InMemoryMonotonicAnchor()
    unanchored = StateJournal(path, integrity_key=KEY, key_id="state-v1")
    unanchored.append(make_commit(1, "exec-crash"))
    unanchored.close()

    recovered = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    assert anchor.read().sequence == 1
    assert recovered.get("exec-crash") is not None
    recovered.close()


def test_anchored_journal_detects_sqlite_snapshot_rollback(tmp_path):
    path = str(tmp_path / "state.sqlite")
    anchor = InMemoryMonotonicAnchor()
    journal = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    journal.append(make_commit(1, "exec-rollback"))
    journal.close()

    db = sqlite3.connect(path)
    db.execute("DELETE FROM state_commits")
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="anchor_mismatch"):
        AnchoredStateJournal(
            path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
        )


def test_anchor_cas_failure_leaves_recoverable_single_record_gap(tmp_path):
    path = str(tmp_path / "state.sqlite")
    anchor = InMemoryMonotonicAnchor()
    journal = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    # Simulate a witness outage after the DB record has committed.
    class FailingAnchor:
        def read(self):
            return anchor.read()
        def compare_and_swap(self, expected, replacement):
            return False
    journal._anchor = FailingAnchor()
    with pytest.raises(RuntimeError, match="anchor_update_failed"):
        journal.append(make_commit(1, "exec-gap"))
    journal.close()

    recovered = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    assert anchor.read().sequence == 1
    assert recovered.get("exec-gap") is not None
    recovered.close()



def test_retry_after_ambiguous_anchor_commit_is_idempotent(tmp_path):
    path = str(tmp_path / "state.sqlite")
    anchor = InMemoryMonotonicAnchor()
    journal = AnchoredStateJournal(
        path, anchor=anchor, integrity_key=KEY, key_id="state-v1"
    )
    class FailingAnchor:
        def read(self):
            return anchor.read()
        def compare_and_swap(self, expected, replacement):
            return False
    commit = make_commit(1, "exec-idempotent")
    journal._anchor = FailingAnchor()
    with pytest.raises(RuntimeError, match="anchor_update_failed"):
        journal.append(commit)
    journal._anchor = anchor
    journal.append(commit)
    assert anchor.read().sequence == 1
    assert journal.get("exec-idempotent") == commit
    journal.close()
