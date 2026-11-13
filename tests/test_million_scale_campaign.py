from __future__ import annotations

import pytest

from core.scenario_matrix import BEHAVIOR_CLASSES, CAPABILITY_CLASSES, IMPACT_CLASSES
from tests.million_scale_campaign import DIFFICULTIES, run_campaign, scenario_for, verify_invariants


def test_scenario_generation_is_reproducible() -> None:
    assert scenario_for(20260906, 123456) == scenario_for(20260906, 123456)
    assert scenario_for(20260906, 123456).digest() == scenario_for(20260906, 123456).digest()


def test_generated_scenario_invariants_hold_across_sample() -> None:
    for case_id in range(10_000):
        verify_invariants(scenario_for(20260906, case_id))


def test_scenario_has_all_requested_dimensions() -> None:
    sample = [scenario_for(20261113, case_id) for case_id in range(10_000)]
    assert {item.capability_class for item in sample} == set(CAPABILITY_CLASSES)
    assert {item.behavior_class for item in sample} == set(BEHAVIOR_CLASSES)
    assert {item.impact_class for item in sample} == set(IMPACT_CLASSES)
    assert len({item.digest() for item in sample}) == len(sample)


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
    assert max(matrix.values()) - min(matrix.values()) <= 1
    assert sum(result["entity_counts"].values()) == 10_000
    assert sum(result["power_counts"].values()) == 10_000


def test_campaign_reports_marginal_coverage_for_every_axis():
    result = run_campaign(20261113, 10_000)
    for key in ("capability_counts", "behavior_counts", "impact_counts"):
        counts = result[key]
        assert sum(counts.values()) == 10_000
        assert all(value > 0 for value in counts.values())


def test_campaign_shard_count_preserves_all_entity_power_strata():
    with pytest.raises(ValueError, match="shard_count_must_be_coprime_with_strata"):
        run_campaign(1, 100, shard_index=0, shards=7)


def test_campaign_reports_pairwise_interaction_histograms():
    result = run_campaign(20261113, 10_000)
    expected_sizes = {
        "entity_behavior_counts": 9 * 8,
        "entity_impact_counts": 9 * 6,
        "power_capability_counts": 7 * 8,
        "capability_impact_counts": 8 * 6,
        "behavior_impact_counts": 8 * 6,
    }
    for key, size in expected_sizes.items():
        counts = result[key]
        assert len(counts) == size
        assert sum(counts.values()) == 10_000
        assert all(value > 0 for value in counts.values())
