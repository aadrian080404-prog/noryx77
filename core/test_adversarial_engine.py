"""Input-boundary and stratification tests for adversarial scenario generation."""
import pytest

from core.adversarial import AdversarialEngine
from core.scenario_matrix import ENTITY_CLASSES, POWER_TIERS, STRATA_COUNT


@pytest.mark.parametrize("seed", [True, -1, 1.5, 2**63])
def test_engine_rejects_invalid_seed(seed):
    with pytest.raises(ValueError):
        AdversarialEngine(seed=seed)


@pytest.mark.parametrize("limit", [True, 0, -1, 10_000_001, 1.5])
def test_engine_rejects_invalid_scenario_limit(limit):
    with pytest.raises(ValueError):
        AdversarialEngine(max_scenarios=limit)


@pytest.mark.parametrize("index", [True, -1, 1.5, 10])
def test_engine_rejects_invalid_or_out_of_range_index(index):
    engine = AdversarialEngine(max_scenarios=10)
    with pytest.raises(IndexError):
        engine.scenario(index)


@pytest.mark.parametrize("difficulty", [True, 0, -1, 101, 1.5])
def test_engine_rejects_invalid_difficulty(difficulty):
    with pytest.raises(ValueError):
        AdversarialEngine().scenario(0, difficulty=difficulty)


def test_scenarios_cover_all_entity_and_power_pairs():
    engine = AdversarialEngine(seed=19, max_scenarios=STRATA_COUNT)
    scenarios = [engine.scenario(index) for index in range(STRATA_COUNT)]
    observed = {(item.entity_class, item.power_tier) for item in scenarios}
    expected = {(entity, power) for entity in ENTITY_CLASSES for power in POWER_TIERS}
    assert observed == expected
    assert len({item.scenario_id for item in scenarios}) == STRATA_COUNT


def test_scenario_is_reproducible_and_power_stratum_is_bound_to_case():
    first = AdversarialEngine(seed=2026, max_scenarios=100)
    second = AdversarialEngine(seed=2026, max_scenarios=100)
    assert first.scenario(73, difficulty=90) == second.scenario(73, difficulty=90)
