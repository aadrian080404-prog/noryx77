from __future__ import annotations

import hashlib
import sqlite3

import pytest

from .contracts import Attestation
from .sqlite_state import SQLiteStateJournal


class AcceptingVerifier:
    def verify(self, attestation, signature):
        return signature == b"s" * 64 and attestation.verified is True


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _attestation(*, previous: str = "0" * 64) -> Attestation:
    return Attestation(
        execution_id="exec-1",
        principal_id="principal-1",
        step_id="step-1",
        agent_id="agent-1",
        agent_key_fingerprint=_digest("agent-key"),
        action_digest=_digest("action"),
        output_digest=_digest("output"),
        verified=True,
        detail="independent-check-passed",
        signature=b"s" * 64,
        previous_attestation_digest=previous,
        runtime_id="runtime-1",
    )


def _journal(path):
    return SQLiteStateJournal(
        str(path),
        integrity_key=b"r" * 32,
        key_id="runtime-kms-key-v1",
        verifier=AcceptingVerifier(),
        runtime_id="runtime-1",
    )


def test_runtime_journal_persists_reservations_and_signed_attestations(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    reservation = journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    assert reservation.step_id == "step-1"
    entry = journal.append(_attestation())
    assert entry.sequence == 0
    assert journal.snapshot() == (entry,)
    journal.close()

    recovered = _journal(path)
    assert recovered.snapshot() == (entry,)
    assert recovered.reservation("exec-1", "step-1") is None
    recovered.close()


def test_runtime_journal_recovers_unresolved_reservation_after_restart(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    journal.close()

    recovered = _journal(path)
    assert recovered.snapshot() == ()
    assert recovered.reservation("exec-1", "step-1") is not None
    recovered.close()


def test_runtime_journal_detects_event_tampering(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    journal.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE runtime_journal_events SET payload_json='{}' WHERE sequence=1")
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="payload_digest_mismatch|authentication_failure"):
        _journal(path)


def test_runtime_journal_rejects_key_id_mismatch(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    journal.close()
    with pytest.raises(RuntimeError, match="key_id_mismatch"):
        SQLiteStateJournal(
            str(path), integrity_key=b"r" * 32, key_id="different-key",
            verifier=AcceptingVerifier(), runtime_id="runtime-1",
        )


def test_runtime_journal_fails_closed_on_concurrent_writer(tmp_path):
    path = tmp_path / "runtime.sqlite"
    first = _journal(path)
    second = _journal(path)
    first.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    with pytest.raises(RuntimeError, match="concurrent_writer_detected"):
        second.reserve_step("exec-2", "principal-2", "step-2", _digest("action-2"))
    with pytest.raises(RuntimeError, match="storage_failed_closed"):
        second.snapshot()
    first.close()
    second.close()


def test_runtime_journal_persists_compensating_rollback_event(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    attestation = _attestation()
    journal.append(attestation)
    journal.rollback_last(attestation)
    assert journal.snapshot() == ()
    journal.close()

    recovered = _journal(path)
    assert recovered.snapshot() == ()
    assert recovered.reservation("exec-1", "step-1") is not None
    recovered.close()


def test_runtime_journal_persists_reservation_restored_after_commit_failure(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    reservation = journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    attestation = _attestation()
    journal.append(attestation)
    journal.restore_reservation(reservation)
    journal.close()

    recovered = _journal(path)
    assert len(recovered.snapshot()) == 1
    assert recovered.reservation("exec-1", "step-1") == reservation
    recovered.close()


def test_runtime_journal_authenticates_event_type(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = _journal(path)
    journal.reserve_step("exec-1", "principal-1", "step-1", _digest("action"))
    journal.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE runtime_journal_events SET event_type='append' WHERE sequence=1")
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="payload_digest_mismatch"):
        _journal(path)
