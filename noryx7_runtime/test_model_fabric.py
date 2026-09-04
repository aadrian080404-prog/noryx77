from dataclasses import dataclass

import pytest

from .model_fabric import ModelFabric, ModelRequest


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
