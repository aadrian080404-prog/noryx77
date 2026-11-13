import pytest
from core.scenario_matrix import ENTITY_CLASSES, MAX_SCENARIO_CASES, POWER_TIERS, STRATA_COUNT, coordinate_for, expected_stratum_counts

def test_every_entity_power_pair_is_covered_evenly():
    counts = {}
    for index in range(STRATA_COUNT * 3):
        item = coordinate_for(123, index)
        key = (item.entity_class, item.power_tier)
        counts[key] = counts.get(key, 0) + 1
    assert len(counts) == len(ENTITY_CLASSES) * len(POWER_TIERS)
    assert set(counts.values()) == {3}

def test_ten_million_partition_is_balanced_and_exact():
    counts = expected_stratum_counts(10_000_000, seed=987)
    assert sum(counts.values()) == 10_000_000
    assert max(counts.values()) - min(counts.values()) <= 1
    assert len(counts) == STRATA_COUNT

def test_scenario_coordinate_is_deterministic_and_seed_sensitive():
    assert coordinate_for(5, 77) == coordinate_for(5, 77)
    assert coordinate_for(5, 77).stratum != coordinate_for(6, 77).stratum

@pytest.mark.parametrize("seed,index", [(True, 0), (-1, 0), (1.2, 0), (0, -1), (0, MAX_SCENARIO_CASES)])
def test_invalid_scenario_coordinates_fail_closed(seed, index):
    with pytest.raises(ValueError):
        coordinate_for(seed, index)
