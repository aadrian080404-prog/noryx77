import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.sqlite_audit import SQLiteAuditLog


def test_sqlite_audit_log_survives_reconstruction(tmp_path):
    path = tmp_path / "audit.sqlite3"
    first = SQLiteAuditLog(path)
    first.record("created", value=1)
    expected_digest = first.digest()

    reopened = SQLiteAuditLog(path)
    assert reopened.snapshot() == ({"event": "created", "value": 1},)
    assert reopened.digest() == expected_digest
    assert reopened.verify_integrity()


def test_independent_instances_serialize_cross_instance_appends(tmp_path):
    path = tmp_path / "audit.sqlite3"
    SQLiteAuditLog(path)

    def write(index):
        SQLiteAuditLog(path).record("parallel", index=index)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(write, range(120)))

    audit = SQLiteAuditLog(path)
    snapshot = audit.snapshot()
    assert len(snapshot) == 120
    assert {entry["index"] for entry in snapshot} == set(range(120))
    assert audit.verify_integrity()


def test_audit_events_reject_normal_update_and_delete(tmp_path):
    path = tmp_path / "audit.sqlite3"
    audit = SQLiteAuditLog(path)
    audit.record("immutable")
    connection = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE noryx7_audit_events SET entry_json = '{}' WHERE sequence = 1")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM noryx7_audit_events WHERE sequence = 1")
    finally:
        connection.close()
    assert audit.verify_integrity()


def test_audit_integrity_detects_database_tampering(tmp_path):
    path = tmp_path / "audit.sqlite3"
    audit = SQLiteAuditLog(path)
    audit.record("original")
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TRIGGER noryx7_audit_events_no_update")
        connection.execute("UPDATE noryx7_audit_events SET entry_json = ? WHERE sequence = 1", ('{"event":"altered"}',))
        connection.commit()
    finally:
        connection.close()
    assert not audit.verify_integrity()


def test_persistent_audit_rejects_memory_database():
    with pytest.raises(ValueError, match="persistent_audit_database_required"):
        SQLiteAuditLog(":memory:")
