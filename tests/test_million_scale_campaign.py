from __future__ import annotations

import pytest

from core.scenario_matrix import (
    ENTITY_CLASSES, POWER_TIERS, CAPABILITY_CLASSES, BEHAVIOR_CLASSES,
    IMPACT_CLASSES, expected_stratum_counts,
)
from tests.million_scale_campaign import DIFFICULTIES, run_campaign, scenario_for, verify_invariants


def test_scenario_generation_is_reproducible() -> None:
    assert scenario_for(20260906, 123456) == scenario_for(20260906, 123456)
    assert scenario_for(20260906, 123456).digest() == scenario_for(20260906, 123456).digest()


def test_generated_scenario_invariants_hold_across_sample() -> None:
    for case_id in range(10_000):
        verify_invariants(scenario_for(20260906, case_id))


def test_campaign_covers_all_difficulty_classes() -> None:
    result = run_campaign(20260906, 100_000)
    counts = result["difficulty_counts"]
    assert set(counts) == set(DIFFICULTIES)
    assert all(counts[name] > 0 for name in DIFFICULTIES)
    assert result["executed"] == 100_000
    assert result["status"] == "passed"


def test_campaign_enforces_difficult_case_quotas() -> None:
    result = run_campaign(20260906, 10_000)
    counts = result["difficulty_counts"]
    assert counts["boundary"] >= 1_000
    assert counts["pathological"] >= 1_500
    assert counts["adversarial"] >= 2_000
    assert counts["compound"] >= 2_500


def test_campaign_is_exactly_budgeted() -> None:
    result = run_campaign(20260906, 50_000)
    assert result["cases"] == 50_000
    assert result["executed"] == 50_000
    assert sum(result["difficulty_counts"].values()) == 50_000


def test_shard_coordinates_are_disjoint_and_complete() -> None:
    total = 1_000
    shards = 5
    coordinates = [case_id for shard in range(shards) for case_id in range(shard, total, shards)]
    assert sorted(coordinates) == list(range(total))
    assert len(coordinates) == len(set(coordinates)) == total


def test_invalid_campaign_budget_fails_closed() -> None:
    with pytest.raises(ValueError):
        run_campaign(1, 0)


def test_invalid_shard_fails_closed() -> None:
    with pytest.raises(ValueError):
        run_campaign(1, 10, shard_index=10, shards=10)



def test_campaign_reports_complete_entity_power_cross_matrix():
    result = run_campaign(20261113, 10_000)
    matrix = result["entity_power_counts"]
    assert len(matrix) == 9 * 7
    assert sum(matrix.values()) == 10_000
    expected = {
        f"{entity}|{power}": 0
        for entity in ENTITY_CLASSES
        for power in POWER_TIERS
    }
    for (entity, power, _, _, _), count in expected_stratum_counts(
        10_000, seed=20261113
    ).items():
        expected[f"{entity}|{power}"] += count
    assert matrix == expected
    assert sum(result["entity_counts"].values()) == 10_000
    assert sum(result["power_counts"].values()) == 10_000


def test_campaign_reports_five_axis_counts_and_full_matrix():
    result = run_campaign(20261113, 10_000)
    assert sum(result["capability_counts"].values()) == 10_000
    assert sum(result["behavior_counts"].values()) == 10_000
    assert sum(result["impact_counts"].values()) == 10_000
    assert sum(result["full_matrix_counts"].values()) == 10_000
    assert len(result["full_matrix_counts"]) == (
        len(ENTITY_CLASSES) * len(POWER_TIERS) * len(CAPABILITY_CLASSES)
        * len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES)
    )


def test_campaign_shards_need_not_be_coprime_with_total_strata():
    result = run_campaign(1, 100, shard_index=0, shards=7)
    assert result["executed"] == 15
    assert result["status"] == "passed"
