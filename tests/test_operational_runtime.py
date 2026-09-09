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


def test_operational_runtime_starts_primary_and_secondary_online():
    fabric = ModelFabric([FakeOperationalModel()], runtime_id="operational-test")
    runtime = OperationalNORYXRuntime(model_fabric=fabric)
    statuses = runtime.agent_runtime.status()
    assert {item.agent_id for item in statuses} >= {"noryx7-llm", "noryx7-secondary"}
    assert all(item.state == "ONLINE" for item in statuses)
    assert runtime.agent_runtime.online is True


def test_operational_runtime_executes_primary_secondary_primary_through_tool_mesh():
    fabric = ModelFabric([FakeOperationalModel()], runtime_id="operational-e2e")
    runtime = OperationalNORYXRuntime(model_fabric=fabric)
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
    assert runtime.agent_runtime.online is True
