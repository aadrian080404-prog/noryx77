from dataclasses import dataclass, replace

from noryx7_runtime.model_fabric import ModelCandidate, ModelFabric, ModelRequest


@dataclass
class FakeModel:
    name: str
    capabilities: frozenset[str] = frozenset({"text"})
    cost_per_call: float = 1.0
    expected_latency_ms: float = 10.0

    def generate(self, prompt: str, *, tools=()):
        return f"{self.name}:{prompt}:{','.join(tools)}"


def _fabric():
    return ModelFabric(
        [FakeModel("model-a"), FakeModel("model-b")],
        runtime_id="runtime-route-binding",
        binding_key=b"r" * 32,
    )


def _request():
    return ModelRequest("compute", runtime_id="runtime-route-binding", min_models=1, max_models=2)


def test_selected_model_tampering_invalidates_bound_result():
    fabric = _fabric()
    request = _request()
    result = fabric.execute(request)
    other = "model-b" if result.selected_model == "model-a" else "model-a"
    tampered = replace(result, selected_model=other)
    assert not fabric.verify_result(request, tampered)


def test_request_digest_tampering_invalidates_bound_result():
    fabric = _fabric()
    request = _request()
    result = fabric.execute(request)
    tampered = replace(result, request_digest="0" * 64)
    assert not fabric.verify_result(request, tampered)


def test_runtime_identity_tampering_invalidates_bound_result():
    fabric = _fabric()
    request = _request()
    result = fabric.execute(request)
    tampered = replace(result, runtime_id="attacker-runtime")
    assert not fabric.verify_result(request, tampered)


def test_candidate_output_tampering_invalidates_bound_result():
    fabric = _fabric()
    request = _request()
    result = fabric.execute(request)
    candidate = result.candidates[0]
    tampered_candidate = replace(candidate, output="attacker-output")
    tampered = replace(result, candidates=(tampered_candidate,) + result.candidates[1:])
    assert not fabric.verify_result(request, tampered)


def test_candidate_replacement_with_stale_digest_is_rejected():
    fabric = _fabric()
    request = _request()
    result = fabric.execute(request)
    candidate = result.candidates[0]
    forged = ModelCandidate(candidate.name, "attacker-output", candidate.latency_ms, candidate.cost, candidate.output_digest)
    tampered = replace(result, candidates=(forged,) + result.candidates[1:])
    assert not fabric.verify_result(request, tampered)
