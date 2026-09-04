from dataclasses import dataclass, replace

import pytest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine
from noryx7_runtime.model_fabric import ModelFabric


@dataclass
class FakeModel:
    name: str = "model-a"
    capabilities: frozenset[str] = frozenset({"text"})
    cost_per_call: float = 1.0
    expected_latency_ms: float = 10.0

    def generate(self, prompt: str, *, tools=()):
        return f"{self.name}:{prompt}:{','.join(tools)}"


def _kernel():
    runtime_id = "runtime-model-binding"
    fabric = ModelFabric([FakeModel()], runtime_id=runtime_id, binding_key=b"k" * 32)
    kernel = Hypersynth(VerificationEngine(), ResourceRouter(), runtime_id=runtime_id, model_fabric=fabric)
    return kernel, fabric


def _run_model():
    kernel, fabric = _kernel()
    task = TaskSpec("t1", "research", "analyze", execution_id="e1")
    agent, request = kernel._model_agent(task, PlanStep("t1:s1", "analyze", "compute", "normal"))
    result = agent.run(task)
    return kernel, fabric, task, agent, request, result


def test_hypersynth_model_agent_binds_verified_request_and_result_digests():
    kernel, fabric, task, agent, request, result = _run_model()
    assert result.model_request_digest == fabric.request_digest(request)
    assert result.model_result_digest == fabric.result_digest(request, agent.last_fabric_result)
    assert result.is_well_formed()


def test_hypersynth_model_result_digest_cannot_be_replaced_without_detection():
    kernel, fabric, task, agent, request, result = _run_model()
    tampered = replace(result, model_result_digest="0" * 64)
    assert tampered.model_result_digest != fabric.result_digest(request, agent.last_fabric_result)
    check = kernel._verify_model_binding(tampered, request, agent.last_fabric_result)
    assert not check.valid
    assert check.reason == "model_result_digest_mismatch"


def test_model_fabric_result_digest_rejects_tampered_result():
    kernel, fabric, task, agent, request, result = _run_model()
    tampered = replace(agent.last_fabric_result, output="attacker-output")
    with pytest.raises(ValueError):
        fabric.result_digest(request, tampered)


def test_hypersynth_model_binding_rejects_forged_request_digest():
    kernel, fabric, task, agent, request, result = _run_model()
    tampered = replace(result, model_request_digest="1" * 64)
    check = kernel._verify_model_binding(tampered, request, agent.last_fabric_result)
    assert not check.valid
    assert check.reason == "model_request_digest_mismatch"


def test_hypersynth_model_binding_rejects_output_swap():
    kernel, fabric, task, agent, request, result = _run_model()
    tampered = replace(result, output="attacker-output")
    check = kernel._verify_model_binding(tampered, request, agent.last_fabric_result)
    assert not check.valid
    assert check.reason == "model_output_binding_mismatch"


def test_hypersynth_model_binding_rejects_stale_fabric_result_for_new_request():
    kernel, fabric, task, agent, request, result = _run_model()
    from noryx7_runtime.model_fabric import ModelRequest
    stale = agent.last_fabric_result
    forged_request = ModelRequest(
        prompt="attacker-request",
        required_capabilities=request.required_capabilities,
        preferred_capabilities=request.preferred_capabilities,
        max_cost=request.max_cost,
        max_latency_ms=request.max_latency_ms,
        min_models=request.min_models,
        max_models=request.max_models,
        tools=request.tools,
        runtime_id=request.runtime_id,
    )
    forged_result = replace(
        result,
        model_request_digest=fabric.request_digest(forged_request),
        model_result_digest=fabric.result_digest(forged_request, stale),
    )
    check = kernel._verify_model_binding(forged_result, forged_request, stale)
    assert not check.valid
    assert check.reason == "model_result_integrity_failure"


def test_hypersynth_model_binding_rejects_missing_fabric_result():
    kernel, fabric, task, agent, request, result = _run_model()
    check = kernel._verify_model_binding(result, request, None)
    assert not check.valid
    assert check.reason == "model_result_integrity_failure"


def test_hypersynth_model_binding_preserves_agent_result_contract():
    kernel, fabric, task, agent, request, result = _run_model()
    assert isinstance(result, AgentResult)
    assert isinstance(result.verification, VerificationResult)
    assert result.verification.valid
    assert result.execution_id == task.execution_id
