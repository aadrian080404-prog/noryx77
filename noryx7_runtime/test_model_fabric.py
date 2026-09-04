from dataclasses import dataclass
from dataclasses import replace
import math

import pytest

from .model_fabric import ModelCandidate, ModelFabric, ModelRequest


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


def test_request_rejects_non_finite_budget_limits():
    with pytest.raises(ValueError):
        ModelRequest("answer", max_cost=math.nan)
    with pytest.raises(ValueError):
        ModelRequest("answer", max_cost=math.inf)
    with pytest.raises(ValueError):
        ModelRequest("answer", max_latency_ms=math.nan)
    with pytest.raises(ValueError):
        ModelRequest("answer", max_latency_ms=math.inf)


def test_result_rejects_non_finite_confidence_and_candidate_economics():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)

    assert fabric.verify_result(request, replace(result, confidence=math.nan)) is False
    assert fabric.verify_result(
        request,
        replace(result, candidates=(replace(result.candidates[0], latency_ms=math.nan),)),
    ) is False
    assert fabric.verify_result(
        request,
        replace(result, candidates=(replace(result.candidates[0], cost=math.inf),)),
    ) is False


def test_result_rejects_malformed_digest_without_raising():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    malformed = replace(
        result,
        candidates=(replace(result.candidates[0], output_digest="not-a-digest"),),
    )
    assert fabric.verify_result(request, malformed) is False


def test_result_digest_fails_closed_for_malformed_candidate():
    model = FakeModel("a", frozenset({"text"}))
    fabric = ModelFabric([model], runtime_id="runtime-a", binding_key=b"x" * 32)
    request = ModelRequest("answer", runtime_id="runtime-a")
    result = fabric.execute(request)
    malformed = replace(result, candidates=(ModelCandidate("a", result.output, math.nan, 1.0, result.candidates[0].output_digest),))
    with pytest.raises(ValueError):
        fabric.result_digest(request, malformed)
