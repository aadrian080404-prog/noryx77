from types import MethodType

import pytest

from core.memory import MemoryStore
from core.operational_runtime import OperationalNORYXRuntime
from core.system_fabric import CanonicalSystemFabric
from gateway.runtime_adapter import RuntimeAdapter


class _Audit:
    def __init__(self):
        self.events = []

    def record(self, event, **payload):
        self.events.append((event, payload))


def _runtime(status="completed"):
    runtime = object.__new__(OperationalNORYXRuntime)
    runtime.memory = MemoryStore()
    runtime.audit = _Audit()
    runtime.system_fabric = CanonicalSystemFabric()

    def heartbeat(self):
        return ()

    def run(self, task):
        if status != "completed":
            return {
                "status": status,
                "task_id": task.task_id,
                "execution_id": task.execution_id,
                "reason": "integration_rejected",
            }
        return {
            "status": "completed",
            "task_id": task.task_id,
            "execution_id": task.execution_id,
            "result": "INTEGRATION PASS",
            "verification": type("V", (), {"valid": True, "stage": "runtime_result", "reason": "output_present"})(),
        }

    runtime.heartbeat_agents = MethodType(heartbeat, runtime)
    runtime.run_hypersynth = MethodType(run, runtime)
    return runtime


def test_gateway_runtime_memory_identity_flow():
    runtime = _runtime()
    adapter = RuntimeAdapter(runtime)

    result = adapter.execute(
        client_id="browser-client-01",
        text="test integration",
        execution_id="exec-01",
    )

    assert result["status"] == "completed"
    assert result["client_id"] == "browser-client-01"
    assert result["execution_id"] == "exec-01"

    input_item = runtime.memory.get("gateway:exec-01:input", execution_id="exec-01")
    output_item = runtime.memory.get("gateway:exec-01:output", execution_id="exec-01")
    assert input_item is not None
    assert input_item.content == "test integration"
    assert output_item is not None
    assert output_item.content == "INTEGRATION PASS"

    records = {
        record.record_id
        for record in runtime.system_fabric.memory.snapshot()
    }
    assert "execution:exec-01:gateway_received" in records
    assert "execution:exec-01:gateway_completed" in records

    events = [event for event, _ in runtime.audit.events]
    assert "gateway_input_bound" in events
    assert "gateway_output_bound" in events


def test_gateway_runtime_rejection_records_canonical_lifecycle():
    runtime = _runtime(status="rejected")
    adapter = RuntimeAdapter(runtime)

    with pytest.raises(PermissionError, match="integration_rejected"):
        adapter.execute(
            client_id="browser-client-02",
            text="test rejection",
            execution_id="exec-rejected",
        )

    records = {
        record.record_id
        for record in runtime.system_fabric.memory.snapshot()
    }
    assert "execution:exec-rejected:gateway_received" in records
    assert "execution:exec-rejected:gateway_rejected" in records

    events = [event for event, _ in runtime.audit.events]
    assert "gateway_execution_rejected" in events


def test_gateway_runtime_rejects_invalid_client():
    runtime = _runtime()
    adapter = RuntimeAdapter(runtime)
    with pytest.raises(PermissionError, match="client_identity_required"):
        adapter.execute(client_id="", text="hello")


def test_gateway_runtime_rejects_oversized_input():
    runtime = _runtime()
    adapter = RuntimeAdapter(runtime)
    with pytest.raises(ValueError, match="browser_input_too_large"):
        adapter.execute(client_id="client", text="x" * 8193)
