import pytest

from core.contracts import TaskSpec
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog


def test_canonical_runtime_uses_and_persists_injected_audit_backend(tmp_path):
    path = str(tmp_path / "runtime-audit.sqlite")
    audit = SQLiteAuditLog(path)
    runtime = NORYXRuntime(audit_log=audit)
    assert runtime.audit is audit
    result = runtime.run(TaskSpec("audit-persist", "compute", "verify persistence", "input"))
    assert result["status"] == "completed"
    assert any(item["event"] == "hypersynth_start" for item in audit.snapshot())
    expected_digest = audit.digest()
    audit.close()

    reopened = SQLiteAuditLog(path)
    assert reopened.verify_integrity()
    assert reopened.digest() == expected_digest
    assert any(item["event"] == "hypersynth_start" for item in reopened.snapshot())
    reopened.close()


def test_canonical_runtime_rejects_non_audit_backend():
    with pytest.raises(TypeError, match="invalid_audit_log"):
        NORYXRuntime(audit_log=object())
