import pytest

from core.adversarial import AdversarialEngine, MAX_SCENARIOS


def test_adversarial_engine_accepts_maximum_scenario_budget():
    engine = AdversarialEngine(seed=1, max_scenarios=MAX_SCENARIOS)
    assert engine.scenario(MAX_SCENARIOS - 1).seed == 1


@pytest.mark.parametrize("seed", [True, -1, 2**63, 1.5, "1"])
def test_adversarial_engine_rejects_invalid_seed(seed):
    with pytest.raises(ValueError, match="invalid_seed"):
        AdversarialEngine(seed=seed)


@pytest.mark.parametrize("budget", [True, 0, -1, MAX_SCENARIOS + 1, 1.5, "10"])
def test_adversarial_engine_rejects_invalid_budget(budget):
    with pytest.raises(ValueError, match="invalid_max_scenarios"):
        AdversarialEngine(max_scenarios=budget)


@pytest.mark.parametrize("index", [True, -1, 1.5, "0", 10])
def test_adversarial_engine_rejects_invalid_scenario_index(index):
    engine = AdversarialEngine(max_scenarios=10)
    with pytest.raises(IndexError, match="scenario_index_out_of_range"):
        engine.scenario(index)


@pytest.mark.parametrize("difficulty", [True, False, 0, 101, 1.5, "5"])
def test_adversarial_engine_rejects_invalid_difficulty(difficulty):
    engine = AdversarialEngine(max_scenarios=10)
    with pytest.raises(ValueError, match="invalid_difficulty"):
        engine.scenario(0, difficulty=difficulty)


def test_adversarial_scenario_exposes_all_matrix_dimensions_reproducibly():
    engine = AdversarialEngine(seed=20261113, max_scenarios=10_000)
    first = engine.scenario(731, difficulty=42)
    second = engine.scenario(731, difficulty=42)
    assert first == second
    assert first.entity_class != ""
    assert first.power_tier.startswith("p")
    assert first.capability_class != ""
    assert first.behavior_class != ""
    assert first.impact_class != ""
