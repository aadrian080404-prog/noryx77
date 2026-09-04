from dataclasses import dataclass

from .agents import ModelFabricAgent
from .contracts import TaskSpec
from noryx7_runtime.model_fabric import ModelFabric
from .verification import VerificationEngine


@dataclass
class FakeModel:
    name: str
    capabilities: frozenset[str]
    cost_per_call: float = 0.0
    expected_latency_ms: float = 1.0

    def generate(self, prompt: str, *, tools=()):
        return f"model:{prompt}"


def test_model_fabric_agent_binds_request_to_runtime():
    fabric = ModelFabric(
        [FakeModel("alpha", frozenset({"reasoning"}))],
        runtime_id="runtime-a",
        binding_key=b"k" * 32,
    )
    agent = ModelFabricAgent(fabric, VerificationEngine())
    task = TaskSpec(
        "step-1", "reasoning", "solve this", None,
        {"runtime_id": "runtime-a", "required_capabilities": ("reasoning",)},
        execution_id="exec-a",
    )
    result = agent.run(task)
    assert result.status == "completed"
    assert result.agent_id == "model_fabric"
    assert result.execution_id == "exec-a"
    assert result.output == "model:solve this"


def test_model_fabric_agent_rejects_cross_runtime_request():
    fabric = ModelFabric(
        [FakeModel("alpha", frozenset({"reasoning"}))],
        runtime_id="runtime-a",
        binding_key=b"k" * 32,
    )
    agent = ModelFabricAgent(fabric, VerificationEngine())
    task = TaskSpec("step-1", "reasoning", "solve this", None, {"runtime_id": "runtime-b"}, execution_id="exec-b")
    result = agent.run(task)
    assert result.status == "rejected"
    assert result.verification is not None
    assert result.verification.reason == "model request runtime identity mismatch"
