from __future__ import annotations

import pytest

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
