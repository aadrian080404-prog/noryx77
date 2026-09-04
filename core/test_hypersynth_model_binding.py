from dataclasses import dataclass, replace

import pytest

from .contracts import TaskSpec
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


def test_hypersynth_model_agent_binds_verified_request_and_result_digests():
    kernel, fabric = _kernel()
    task = TaskSpec("t1", "research", "analyze", execution_id="e1")
    agent, request = kernel._model_agent(task, PlanStep("t1:s1", "analyze", "compute", "normal"))
    result = agent.run(task)
    assert result.model_request_digest == fabric.request_digest(request)
    assert result.model_result_digest == fabric.result_digest(request, agent.last_fabric_result)
    assert result.is_well_formed()


def test_hypersynth_model_result_digest_cannot_be_replaced_without_detection():
    kernel, fabric = _kernel()
    task = TaskSpec("t1", "research", "analyze", execution_id="e1")
    agent, request = kernel._model_agent(task, PlanStep("t1:s1", "analyze", "compute", "normal"))
    result = agent.run(task)
    tampered = replace(result, model_result_digest="0" * 64)
    assert tampered.model_result_digest != fabric.result_digest(request, agent.last_fabric_result)


def test_model_fabric_result_digest_rejects_tampered_result():
    kernel, fabric = _kernel()
    task = TaskSpec("t1", "research", "analyze", execution_id="e1")
    agent, request = kernel._model_agent(task, PlanStep("t1:s1", "analyze", "compute", "normal"))
    result = agent.run(task)
    tampered = replace(agent.last_fabric_result, output="attacker-output")
    with pytest.raises(ValueError):
        fabric.result_digest(request, tampered)
