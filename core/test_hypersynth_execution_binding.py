from dataclasses import dataclass, replace

import pytest

from .contracts import AgentResult, TaskSpec
from .hypersynth import Hypersynth
from .planning import PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine
from noryx7_runtime.model_fabric import ModelFabric, ModelRequest


@dataclass
class FakeModel:
    name: str = "model-a"
    capabilities: frozenset[str] = frozenset({"text"})
    cost_per_call: float = 1.0
    expected_latency_ms: float = 10.0

    def generate(self, prompt: str, *, tools=()):
        return f"{self.name}:{prompt}:{','.join(tools)}"


def _kernel():
    runtime_id = "runtime-execution-binding"
    fabric = ModelFabric([FakeModel()], runtime_id=runtime_id, binding_key=b"k" * 32)
    return Hypersynth(VerificationEngine(), ResourceRouter(), runtime_id=runtime_id, model_fabric=fabric), fabric


def _run(execution_id: str):
    kernel, fabric = _kernel()
    task = TaskSpec("task", "research", "analyze", execution_id=execution_id)
    agent, request = kernel._model_agent(task, PlanStep("task:s1", "analyze", "compute", "normal"))
    result = agent.run(task)
    return kernel, fabric, task, agent, request, result


def test_model_request_is_bound_to_task_execution():
    kernel, fabric, task, agent, request, result = _run("execution-a")
    assert request.execution_id == task.execution_id
    assert result.execution_id == task.execution_id
    assert fabric.request_digest(request) == result.model_request_digest


def test_valid_fabric_result_cannot_cross_execution():
    kernel_a, fabric_a, task_a, agent_a, request_a, result_a = _run("execution-a")
    kernel_b, fabric_b, task_b, agent_b, request_b, result_b = _run("execution-b")
    assert request_a.execution_id != request_b.execution_id
    assert fabric_b.verify_result(request_b, agent_a.last_fabric_result) is False
    swapped = replace(result_a, execution_id=task_b.execution_id)
    check = kernel_b._verify_model_binding(swapped, request_b, agent_a.last_fabric_result)
    assert check.valid is False


def test_request_and_result_digests_cannot_be_reused_across_executions():
    kernel_a, fabric_a, task_a, agent_a, request_a, result_a = _run("execution-a")
    kernel_b, fabric_b, task_b, agent_b, request_b, result_b = _run("execution-b")
    assert fabric_b.request_digest(request_b) != fabric_a.request_digest(request_a)
    swapped = replace(result_b, model_request_digest=result_a.model_request_digest, model_result_digest=result_a.model_result_digest)
    check = kernel_b._verify_model_binding(swapped, request_b, agent_b.last_fabric_result)
    assert check.valid is False
    assert check.reason == "model_request_digest_mismatch"


def test_execution_id_tampering_is_rejected_before_model_binding():
    kernel, fabric, task, agent, request, result = _run("execution-a")
    tampered = replace(result, execution_id="execution-attacker")
    check = kernel._verify_model_binding(tampered, request, agent.last_fabric_result)
    assert check.valid is False
    assert check.reason == "model_execution_identity_mismatch"


def test_model_agent_rejects_child_execution_swap_before_fabric_call():
    kernel, fabric, task, agent, request, result = _run("execution-a")
    foreign_child = replace(task, execution_id="execution-b")
    with pytest.raises(RuntimeError, match="model_execution_identity_mismatch"):
        agent.run(foreign_child)


def test_model_request_execution_id_tampering_changes_binding_digest():
    kernel, fabric, task, agent, request, result = _run("execution-a")
    tampered_request = replace(request, execution_id="execution-b")
    assert fabric.request_digest(tampered_request) != fabric.request_digest(request)
    assert fabric.verify_result(tampered_request, agent.last_fabric_result) is False


def test_agent_result_contract_remains_execution_bound_after_model_binding():
    kernel, fabric, task, agent, request, result = _run("execution-a")
    assert isinstance(result, AgentResult)
    assert result.is_well_formed()
    assert result.execution_id == request.execution_id == task.execution_id
