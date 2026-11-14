import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.audit import AuditLog
from core.sqlite_audit import SQLiteAuditLog
from core.crypto import InMemoryKeyProvider


def test_sqlite_audit_log_is_a_drop_in_auditlog_and_survives_restart(tmp_path):
    path = str(tmp_path / "audit.sqlite")
    audit = SQLiteAuditLog(path)
    assert isinstance(audit, AuditLog)
    audit.record("task.started", task_id="t-1")
    audit.record("task.completed", task_id="t-1", result_digest="a" * 64)
    expected_digest = audit.digest()
    provider = InMemoryKeyProvider({"audit-key": b"k" * 32})
    checkpoint = audit.checkpoint(provider, key_id="audit-key")
    assert audit.verify_integrity()
    audit.close()

    reopened = SQLiteAuditLog(path)
    assert [item["event"] for item in reopened.snapshot()] == [
        "task.started", "task.completed"
    ]
    assert reopened.digest() == expected_digest
    assert reopened.verify_integrity()
    assert reopened.verify_checkpoint(checkpoint, provider)
    reopened.close()


def test_sqlite_audit_log_serializes_multiple_instances(tmp_path):
    path = str(tmp_path / "shared.sqlite")
    logs = [SQLiteAuditLog(path), SQLiteAuditLog(path)]
    def write(index):
        logs[index % 2].record("parallel.write", index=index)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(40)))
    verifier = SQLiteAuditLog(path)
    events = verifier.snapshot()
    assert len(events) == 40
    assert {item["index"] for item in events} == set(range(40))
    assert verifier.verify_integrity()
    for log in logs:
        log.close()
    verifier.close()


def test_sqlite_audit_log_rejects_non_json_and_detects_tampering(tmp_path):
    path = str(tmp_path / "tamper.sqlite")
    audit = SQLiteAuditLog(path)
    with pytest.raises(ValueError, match="serializable"):
        audit.record("bad", secret=object())
    audit.record("safe", value="original")
    audit.close()

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE audit_events SET event_json=? WHERE sequence=1",
            ('{"event":"safe","value":"changed"}',),
        )
    reopened = SQLiteAuditLog(path)
    assert not reopened.verify_integrity()
    provider = InMemoryKeyProvider({"audit-key": b"k" * 32})
    with pytest.raises(ValueError, match="integrity"):
        reopened.checkpoint(provider, key_id="audit-key")
    reopened.close()


def test_sqlite_audit_log_rejects_invalid_configuration(tmp_path):
    with pytest.raises(ValueError, match="path"):
        SQLiteAuditLog("")
    with pytest.raises(ValueError, match="timeout"):
        SQLiteAuditLog(str(tmp_path / "audit.sqlite"), busy_timeout_ms=0)
