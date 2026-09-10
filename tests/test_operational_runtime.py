from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime
from noryx7_runtime.model_fabric import ModelFabric


class FakeOperationalModel:
    name = "fake-operational"
    capabilities = frozenset({"text"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        if "Begin the response with exactly APPROVE or REJECT" in prompt:
            return "APPROVE: the proposal is internally consistent; no external execution is claimed."
        if "Reconcile the Primary proposal with the Secondary critique" in prompt:
            return "RECONCILED: proposal retained after secondary cross-check."
        return "PRIMARY PROPOSAL: bounded answer produced for the requested task."


def _runtime(name="operational-test"):
    fabric = ModelFabric([FakeOperationalModel()], runtime_id=name)
    return OperationalNORYXRuntime(model_fabric=fabric)


def test_operational_runtime_starts_primary_and_secondary_online():
    runtime = _runtime()
    statuses = runtime.agent_runtime.status()
    assert {item.agent_id for item in statuses} >= {"noryx7-llm", "noryx7-secondary"}
    assert all(item.state == "ONLINE" for item in statuses)
    assert runtime.agent_runtime.online is True


def test_operational_runtime_executes_primary_secondary_primary_through_tool_mesh():
    runtime = _runtime("operational-e2e")
    task = TaskSpec(
        task_id="operational-e2e-task",
        task_type="conversation",
        objective="Produce a bounded answer and cross-check it with the secondary agent.",
        input="test",
        constraints={},
        verification_requirements=("agent_result",),
        risk_class="normal",
        execution_id="execution-operational-e2e",
    )
    result = runtime.run_hypersynth(task)
    assert result["status"] == "completed"
    assert result["execution_id"] == task.execution_id
    assert result["results"][-1].output.startswith("RECONCILED:")
    events = runtime.audit.snapshot()
    assert any(event.get("event") == "agent_collaboration_completed" for event in events)

    record_ids = {record.record_id for record in runtime.system_fabric.memory.snapshot()}
    assert "execution:execution-operational-e2e:runtime_received" in record_ids
    assert "execution:execution-operational-e2e:runtime_committed" in record_ids
    assert runtime.agent_runtime.online is True


def test_operational_runtime_generates_execution_identity_when_task_omits_one():
    runtime = _runtime("operational-generated-id")
    task = TaskSpec(
        task_id="operational-generated-id-task",
        task_type="conversation",
        objective="Produce a bounded answer.",
        input="test",
        constraints={},
        verification_requirements=("agent_result",),
        risk_class="normal",
    )
    result = runtime.run_hypersynth(task)
    execution_id = result.get("execution_id")
    assert result["status"] == "completed"
    assert isinstance(execution_id, str) and execution_id
    assert task.execution_id == ""

    record_ids = {record.record_id for record in runtime.system_fabric.memory.snapshot()}
    assert f"execution:{execution_id}:runtime_received" in record_ids
    assert f"execution:{execution_id}:runtime_committed" in record_ids
