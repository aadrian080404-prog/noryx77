from dataclasses import dataclass, replace

from .model_fabric import ModelFabric, ModelRequest


@dataclass
class FakeModel:
    name: str = "a"
    capabilities: frozenset[str] = frozenset({"text"})
    cost_per_call: float = 1.0
    expected_latency_ms: float = 10.0

    def generate(self, prompt: str, *, tools=()):
        return f"{self.name}:{prompt}"


def test_execution_identity_is_part_of_request_provenance():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-a", binding_key=b"x" * 32)
    request_a = ModelRequest("answer", runtime_id="runtime-a", execution_id="execution-a")
    request_b = ModelRequest("answer", runtime_id="runtime-a", execution_id="execution-b")
    assert fabric.request_digest(request_a) != fabric.request_digest(request_b)


def test_bound_result_cannot_replay_across_execution_identity():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-a", binding_key=b"x" * 32)
    request_a = ModelRequest("answer", runtime_id="runtime-a", execution_id="execution-a")
    request_b = ModelRequest("answer", runtime_id="runtime-a", execution_id="execution-b")
    result_a = fabric.execute(request_a)
    assert fabric.verify_result(request_a, result_a) is True
    assert fabric.verify_result(request_b, result_a) is False


def test_execution_identity_tampering_invalidates_result_binding():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a", execution_id="execution-a")
    result = fabric.execute(request)
    forged_request = replace(request, execution_id="execution-b")
    assert fabric.verify_result(forged_request, result) is False
