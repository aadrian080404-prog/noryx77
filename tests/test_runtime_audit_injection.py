import pytest

from core.audit import AuditLog
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog


def test_runtime_injects_durable_audit_log_into_all_runtime_layers(tmp_path):
    database = tmp_path / "runtime-audit.sqlite3"
    audit = SQLiteAuditLog(database)
    runtime = NORYXRuntime(audit_log=audit)

    assert runtime.audit is audit
    assert runtime.hypersynth.audit is audit

    runtime.audit.record("runtime_audit_injection_verified", source="test")
    assert runtime.audit.verify_integrity()

    reopened = SQLiteAuditLog(database)
    restored_runtime = NORYXRuntime(audit_log=reopened)
    events = restored_runtime.audit.snapshot()
    assert events[-1] == {
        "event": "runtime_audit_injection_verified",
        "source": "test",
    }


def test_runtime_keeps_in_memory_audit_as_default():
    runtime = NORYXRuntime()
    assert isinstance(runtime.audit, AuditLog)
    assert not isinstance(runtime.audit, SQLiteAuditLog)


def test_runtime_rejects_invalid_audit_log_dependency():
    with pytest.raises(TypeError, match="invalid_audit_log"):
        NORYXRuntime(audit_log=object())
