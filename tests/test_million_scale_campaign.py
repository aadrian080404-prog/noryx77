from __future__ import annotations

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


def test_campaign_is_exactly_budgeted() -> None:
    result = run_campaign(20260906, 50_000)
    assert result["cases"] == 50_000
    assert sum(result["difficulty_counts"].values()) == 50_000
