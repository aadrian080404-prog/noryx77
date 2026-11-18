import pytest

from core.audit import AuditLog
from core.journal_integrity import InMemoryMonotonicAnchor
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog


def test_runtime_publishes_durable_audit_head_to_external_anchor(tmp_path):
    audit = SQLiteAuditLog(str(tmp_path / "runtime-anchor.sqlite3"))
    runtime = NORYXRuntime(audit_log=audit)
    anchor = InMemoryMonotonicAnchor()
    audit.record("verified_execution_committed", execution_id="execution-1")

    head = runtime.checkpoint_audit_anchor(anchor)
    assert head.sequence == 1
    assert anchor.read() == head
    audit.close()


def test_runtime_refuses_anchor_checkpoint_without_durable_backend():
    runtime = NORYXRuntime(audit_log=AuditLog())
    with pytest.raises(RuntimeError, match="durable_audit_anchor_backend_required"):
        runtime.checkpoint_audit_anchor(InMemoryMonotonicAnchor())
