import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.sqlite_federated_audit import SQLiteFederatedAuditLog


def test_sqlite_audit_survives_restart_and_verifies_hash_chain(tmp_path):
    path = tmp_path / "federated-audit.sqlite"
    first = SQLiteFederatedAuditLog(path, clock=lambda: 100.0)
    first.record("federated_action_decision", principal_id="p-1", action_id="a-1")
    first.record("federated_action_outcome", principal_id="p-1", outcome="dispatched")
    digest = first.digest()
    assert first.verify_integrity()
    first.close()

    second = SQLiteFederatedAuditLog(path, clock=lambda: 101.0)
    assert second.verify_integrity()
    assert second.digest() == digest
    assert [row["event"] for row in second.snapshot()] == [
        "federated_action_decision", "federated_action_outcome"
    ]
    second.record("federated_action_outcome", principal_id="p-2", outcome="executor_failed")
    assert len(second.snapshot()) == 3
    second.close()


def test_sqlite_audit_rejects_mutation_and_detects_out_of_band_corruption(tmp_path):
    path = tmp_path / "federated-audit.sqlite"
    audit = SQLiteFederatedAuditLog(path)
    audit.record("federated_action_decision", principal_id="p-1")
    with pytest.raises(sqlite3.IntegrityError, match="federated_audit_append_only"):
        audit._conn.execute(
            "UPDATE federated_audit_events SET event_json='{}' WHERE sequence=1"
        )
    audit.close()

    tamper = sqlite3.connect(path)
    tamper.execute("DROP TRIGGER federated_audit_no_update")
    tamper.execute(
        "UPDATE federated_audit_events SET event_json='{}' WHERE sequence=1"
    )
    tamper.commit()
    tamper.close()
    with pytest.raises(RuntimeError, match="federated_audit_integrity_failed"):
        SQLiteFederatedAuditLog(path)


def test_sqlite_audit_serializes_concurrent_appends_without_sequence_gaps(tmp_path):
    audit = SQLiteFederatedAuditLog(tmp_path / "concurrent.sqlite")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: audit.record("worker_event", worker=n), range(40)))
    snapshot = audit.snapshot()
    assert len(snapshot) == 40
    assert audit.verify_integrity()
    assert len({row["worker"] for row in snapshot}) == 40
    audit.close()


def test_sqlite_audit_requires_a_file_backed_database_and_valid_clock(tmp_path):
    with pytest.raises(ValueError, match="durable_audit_database_required"):
        SQLiteFederatedAuditLog(":memory:")
    audit = SQLiteFederatedAuditLog(tmp_path / "invalid-clock.sqlite", clock=lambda: float("nan"))
    with pytest.raises(RuntimeError, match="audit_clock_invalid"):
        audit.record("test")
    assert audit.snapshot() == ()
    audit.close()
