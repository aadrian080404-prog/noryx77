import hashlib
import sqlite3

import pytest

from noryx7_runtime.contracts import Attestation
from noryx7_runtime.durable_state import DurableStateJournal


KEY = b"runtime-journal-test-key-material-32-bytes-minimum"
KEY_ID = "test-key-v1"
FINGERPRINT = hashlib.sha256(b"legacy-executor").hexdigest()


def make_attestation():
    return Attestation(
        execution_id="execution-1",
        principal_id="principal-1",
        step_id="step-1",
        agent_id="executor",
        agent_key_fingerprint=FINGERPRINT,
        action_digest="1" * 64,
        output_digest="2" * 64,
        verified=True,
        detail="verified",
        previous_attestation_digest="0" * 64,
    )


def open_journal(path):
    return DurableStateJournal(
        str(path),
        integrity_key=KEY,
        key_id=KEY_ID,
        require_signatures=False,
    )


def test_pending_reservation_survives_restart_and_blocks_duplicate(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = open_journal(path)
    reservation = journal.reserve_step(
        "execution-1", "principal-1", "step-1", "1" * 64
    )
    journal.close()

    recovered = open_journal(path)
    assert recovered.reservation("execution-1", "step-1") == reservation
    with pytest.raises(ValueError, match="already reserved"):
        recovered.reserve_step(
            "execution-1", "principal-1", "step-1", "1" * 64
        )
    recovered.close()


def test_attestation_and_reservation_resolution_survive_restart(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = open_journal(path)
    journal.reserve_step("execution-1", "principal-1", "step-1", "1" * 64)
    journal.append(make_attestation())
    journal.close()

    recovered = open_journal(path)
    entries = recovered.snapshot()
    assert len(entries) == 1
    assert entries[0].execution_id == "execution-1"
    assert entries[0].step_id == "step-1"
    assert recovered.reservation("execution-1", "step-1") is None
    with pytest.raises(ValueError, match="duplicate execution step"):
        recovered.append(make_attestation())
    recovered.close()


def test_tampered_event_is_rejected_on_recovery(tmp_path):
    path = tmp_path / "runtime.sqlite"
    journal = open_journal(path)
    journal.reserve_step("execution-1", "principal-1", "step-1", "1" * 64)
    journal.close()

    db = sqlite3.connect(path)
    db.execute(
        "UPDATE runtime_events SET event_json = ? WHERE sequence = 1",
        ('{"payload":{},"type":"reservation"}',),
    )
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="integrity_failure"):
        open_journal(path)


def test_integrity_key_must_be_external_strength(tmp_path):
    with pytest.raises(ValueError, match="at_least_32_bytes"):
        DurableStateJournal(
            str(tmp_path / "weak.sqlite"),
            integrity_key=b"too-short",
            key_id=KEY_ID,
            require_signatures=False,
        )
