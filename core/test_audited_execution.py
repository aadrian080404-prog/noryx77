import pytest

from core.audit import AuditLog
from core.execution_fabric import ExecutionFabric, ProposedAction
from core.audited_execution import AuditedExecutionFabric


class Adapter:
    environment = "test"

    def __init__(self):
        self.calls = 0

    def observe(self):
        return None

    def execute(self, action):
        self.calls += 1
        return {"ok": True}


def action(parameters=None):
    return ProposedAction("test", "a-1", "write", "resource",
                          parameters if parameters is not None else {"value": "secret"})


def test_audited_execution_records_intent_and_outcome_without_raw_parameters():
    audit = AuditLog()
    adapter = Adapter()
    fabric = ExecutionFabric(authorize=lambda _: True)
    fabric.register(adapter)
    audited = AuditedExecutionFabric(fabric, audit)
    assert audited.execute(action()) == {"ok": True}
    events = audit.snapshot()
    assert [item["event"] for item in events] == [
        "execution.requested", "execution.completed"
    ]
    assert all("secret" not in repr(item) for item in events)
    assert audit.verify_integrity()


def test_audit_intent_failure_prevents_execution(monkeypatch):
    audit = AuditLog()
    adapter = Adapter()
    fabric = ExecutionFabric(authorize=lambda _: True)
    fabric.register(adapter)
    audited = AuditedExecutionFabric(fabric, audit)
    monkeypatch.setattr(audit, "record", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        audited.execute(action())
    assert adapter.calls == 0


def test_authorization_failure_is_audited_and_rethrown():
    audit = AuditLog()
    adapter = Adapter()
    fabric = ExecutionFabric(authorize=lambda _: False)
    fabric.register(adapter)
    audited = AuditedExecutionFabric(fabric, audit)
    with pytest.raises(PermissionError):
        audited.execute(action())
    assert [item["event"] for item in audit.snapshot()] == [
        "execution.requested", "execution.failed"
    ]
    assert adapter.calls == 0


def test_non_json_and_oversized_parameters_are_rejected_before_audit():
    audit = AuditLog()
    fabric = ExecutionFabric(authorize=lambda _: True)
    audited = AuditedExecutionFabric(fabric, audit)
    with pytest.raises(ValueError, match="not_auditable"):
        audited.execute(action({"value": object()}))
    assert audit.snapshot() == ()
