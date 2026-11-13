import pytest

from core.adversarial import AdversarialEngine, MAX_SCENARIOS
from core.scenario_matrix import (
    CAPABILITY_CLASSES, BEHAVIOR_CLASSES, IMPACT_CLASSES, STRATA_COUNT,
)


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


def test_adversarial_engine_scenarios_expose_all_five_matrix_dimensions():
    engine = AdversarialEngine(seed=20261113, max_scenarios=STRATA_COUNT)
    scenarios = [engine.scenario(index) for index in range(STRATA_COUNT)]
    assert {item.capability_class for item in scenarios} == set(CAPABILITY_CLASSES)
    assert {item.behavior_class for item in scenarios} == set(BEHAVIOR_CLASSES)
    assert {item.impact_class for item in scenarios} == set(IMPACT_CLASSES)
    assert len({
        (
            item.entity_class, item.power_tier, item.capability_class,
            item.behavior_class, item.impact_class,
        )
        for item in scenarios
    }) == STRATA_COUNT
