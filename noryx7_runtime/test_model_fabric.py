from dataclasses import dataclass
from dataclasses import replace
import math

import pytest

from .model_fabric import FabricResult, ModelCandidate, ModelFabric, ModelRequest


@dataclass
class FakeModel:
    name: str
    capabilities: frozenset[str]
    cost_per_call: float = 1.0
    expected_latency_ms: float = 10.0
    fail: bool = False

    def generate(self, prompt: str, *, tools=()):
        if self.fail:
            raise RuntimeError("provider failure")
        return f"{self.name}:{prompt}:{','.join(tools)}"


def test_routes_by_required_and_preferred_capabilities():
    fabric = ModelFabric([
        FakeModel("fast", frozenset({"text"}), expected_latency_ms=5),
        FakeModel("reasoner", frozenset({"text", "reasoning"}), expected_latency_ms=20),
        FakeModel("vision", frozenset({"text", "vision"}), expected_latency_ms=30),
    ])
    request = ModelRequest("solve", frozenset({"reasoning"}), frozenset({"reasoning"}), max_models=1)
    assert fabric.route(request) == ("reasoner",)


def test_provider_failure_degrades_without_losing_quorum():
    fabric = ModelFabric([
        FakeModel("a", frozenset({"text"}), fail=True),
        FakeModel("b", frozenset({"text"})),
    ])
    result = fabric.execute(ModelRequest("hello", min_models=1, max_models=2))
    assert result.selected_model == "b"
    assert result.degraded is True


def test_required_capability_failure_is_fail_closed():
    fabric = ModelFabric([FakeModel("text", frozenset({"text"}))])
    with pytest.raises(RuntimeError):
        fabric.execute(ModelRequest("inspect", frozenset({"vision"})))


def test_verifier_can_override_low_latency_first_choice():
    fabric = ModelFabric([
        FakeModel("cheap", frozenset({"text"}), cost_per_call=0.1, expected_latency_ms=1),
        FakeModel("strong", frozenset({"text"}), cost_per_call=2.0, expected_latency_ms=50),
    ])
    result = fabric.execute(
        ModelRequest("answer", min_models=2, max_models=2),
        verifier=lambda name, output: 0.9 if name == "strong" else 0.2,
    )
    assert result.selected_model == "strong"
    assert result.confidence == 0.9


def test_synthesizer_receives_all_successful_candidates():
    fabric = ModelFabric([
        FakeModel("a", frozenset({"text"})),
        FakeModel("b", frozenset({"text"})),
    ])
    result = fabric.execute(
        ModelRequest("answer", min_models=2, max_models=2),
        synthesizer=lambda candidates: "+".join(c.name for c in candidates),
    )
    assert result.output == "a+b"


def test_bound_fabric_requires_strong_binding_key_and_runtime():
    model = FakeModel("a", frozenset({"text"}))
    with pytest.raises(ValueError):
        ModelFabric([model], runtime_id="runtime-a", binding_key=b"short")
    with pytest.raises(ValueError):
        ModelFabric([model], binding_key=b"x" * 32)


def test_bound_result_cannot_cross_runtime():
    model = FakeModel("a", frozenset({"text"}))
    fabric_a = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request_a = ModelRequest("answer", runtime_id="runtime-a")
    result_a = fabric_a.execute(request_a)

    fabric_b = ModelFabric([model], runtime_id="runtime-b", binding_key=b"x" * 32)
    request_b = ModelRequest("answer", runtime_id="runtime-b")
    assert fabric_b.verify_result(request_b, result_a) is False


def test_bound_result_rejects_output_tampering():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    tampered = replace(result, output="attacker-output")
    assert fabric.verify_result(request, tampered) is False


def test_bound_result_rejects_request_replay_under_different_request():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    replay = ModelRequest("different-answer", runtime_id="runtime-a")
    assert fabric.verify_result(replay, result) is False


def test_result_confidence_nan_and_infinity_are_rejected():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    assert fabric.verify_result(request, replace(result, confidence=math.nan)) is False
    assert fabric.verify_result(request, replace(result, confidence=math.inf)) is False


def test_result_candidate_count_and_selected_model_are_bounded():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    assert fabric.verify_result(request, replace(result, candidates=())) is False
    assert fabric.verify_result(request, replace(result, selected_model="unknown")) is False


def test_request_rejects_non_finite_limits_and_boolean_fanout():
    with pytest.raises(ValueError):
        ModelRequest("answer", max_cost=math.inf)
    with pytest.raises(ValueError):
        ModelRequest("answer", max_latency_ms=math.nan)
    with pytest.raises(ValueError):
        ModelRequest("answer", min_models=True)
    with pytest.raises(ValueError):
        ModelRequest("answer", max_models=False)


def _bound_fabric_and_result():
    models = [
        FakeModel("a", frozenset({"text"}), expected_latency_ms=5),
        FakeModel("b", frozenset({"text"}), expected_latency_ms=10),
    ]
    fabric = ModelFabric(models, runtime_id="runtime-a", binding_key=b"k" * 32)
    request = ModelRequest("answer", min_models=2, max_models=2, runtime_id="runtime-a")
    return fabric, request, fabric.execute(request)


def test_result_rejects_selected_model_substitution():
    fabric, request, result = _bound_fabric_and_result()
    replacement = "b" if result.selected_model == "a" else "a"
    assert fabric.verify_result(request, replace(result, selected_model=replacement)) is False


def test_result_rejects_candidate_insertion_removal_and_reordering():
    fabric, request, result = _bound_fabric_and_result()
    a, b = result.candidates
    assert fabric.verify_result(request, replace(result, candidates=(a,))) is False
    forged = ModelCandidate("attacker", "forged", a.latency_ms, a.cost, a.output_digest)
    assert fabric.verify_result(request, replace(result, candidates=(forged, b))) is False
    assert fabric.verify_result(request, replace(result, candidates=(b, a))) is False


def test_result_rejects_candidate_metadata_tampering():
    fabric, request, result = _bound_fabric_and_result()
    candidate = result.candidates[0]
    assert fabric.verify_result(request, replace(result, candidates=(replace(candidate, latency_ms=candidate.latency_ms + 1), result.candidates[1]))) is False
    assert fabric.verify_result(request, replace(result, candidates=(replace(candidate, cost=candidate.cost + 1), result.candidates[1]))) is False
    assert fabric.verify_result(request, replace(result, candidates=(replace(candidate, output_digest="0" * 64), result.candidates[1]))) is False


def test_result_rejects_result_mac_and_envelope_digest_tampering():
    fabric, request, result = _bound_fabric_and_result()
    assert fabric.verify_result(request, replace(result, result_mac="0" * 64)) is False
    assert fabric.verify_result(request, replace(result, request_digest="0" * 64)) is False


def test_result_rejects_confidence_and_degraded_flag_tampering():
    fabric, request, result = _bound_fabric_and_result()
    assert fabric.verify_result(request, replace(result, confidence=1.0 if result.confidence == 0.0 else 0.0)) is False
    assert fabric.verify_result(request, replace(result, degraded=not result.degraded)) is False


def test_verifier_rejects_boolean_and_non_finite_scores_fail_closed():
    fabric = ModelFabric([FakeModel("a", frozenset({"text"}))])
    request = ModelRequest("answer")
    with pytest.raises(RuntimeError, match="model_verification_failure"):
        fabric.execute(request, verifier=lambda name, output: True)
    with pytest.raises(RuntimeError, match="model_verification_failure"):
        fabric.execute(request, verifier=lambda name, output: math.nan)
    with pytest.raises(RuntimeError, match="model_verification_failure"):
        fabric.execute(request, verifier=lambda name, output: math.inf)


def test_synthesizer_failure_is_fail_closed():
    fabric = ModelFabric([FakeModel("a", frozenset({"text"}))])
    request = ModelRequest("answer")
    with pytest.raises(RuntimeError, match="model_synthesis_failure"):
        fabric.execute(request, synthesizer=lambda candidates: (_ for _ in ()).throw(ValueError("tampered")))


def test_synthesized_output_is_bound_to_final_result_integrity():
    fabric = ModelFabric([FakeModel("a", frozenset({"text"})), FakeModel("b", frozenset({"text"}))], runtime_id="runtime-a", binding_key=b"k" * 32)
    request = ModelRequest("answer", min_models=2, max_models=2, runtime_id="runtime-a")
    result = fabric.execute(request, synthesizer=lambda candidates: "trusted-synthesis")
    assert result.output == "trusted-synthesis"
    assert fabric.verify_result(request, result)
    assert fabric.verify_result(request, replace(result, output="attacker-synthesis")) is False


def test_result_rejects_candidate_name_output_digest_mismatch():
    fabric, request, result = _bound_fabric_and_result()
    candidate = result.candidates[0]
    forged = replace(candidate, name="b" if candidate.name == "a" else "a")
    assert fabric.verify_result(request, replace(result, candidates=(forged, result.candidates[1]))) is False


def test_fabric_result_shape_is_not_mutable_into_a_valid_cross_request_replay():
    fabric, request, result = _bound_fabric_and_result()
    other_request = ModelRequest("different", min_models=2, max_models=2, runtime_id="runtime-a")
    forged = replace(result, request_digest=fabric.request_digest(other_request))
    assert fabric.verify_result(other_request, forged) is False
