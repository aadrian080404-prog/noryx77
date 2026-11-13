from __future__ import annotations

import pytest

from core.scenario_matrix import ENTITY_CLASSES, POWER_TIERS
from tests.million_scale_campaign import scenario_for
from tests.aggregate_campaign import aggregate_results


def _shards(cases: int, seed: int, shards: int):
    results = []
    for shard_index in range(shards):
        difficulty = {name: 0 for name in ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")}
        entities = {name: 0 for name in ENTITY_CLASSES}
        powers = {name: 0 for name in POWER_TIERS}
        matrix = {f"{entity}|{power}": 0 for entity in ENTITY_CLASSES for power in POWER_TIERS}
        executed = 0
        for case_id in range(shard_index, cases, shards):
            scenario = scenario_for(seed, case_id)
            difficulty[scenario.difficulty] += 1
            entities[scenario.entity_class] += 1
            powers[scenario.power_tier] += 1
            matrix[f"{scenario.entity_class}|{scenario.power_tier}"] += 1
            executed += 1
        results.append({
            "seed": seed, "cases": cases, "executed": executed,
            "shard_index": shard_index, "shards": shards,
            "difficulty_counts": difficulty, "entity_counts": entities,
            "power_counts": powers, "entity_power_counts": matrix,
            "verification_scope": "one_structural_preflight_plus_synthetic_scenario_invariants",
            "status": "passed",
        })
    return results


def test_aggregates_all_shards_and_exact_strata():
    result = aggregate_results(_shards(126, 7, 2), cases=126, seed=7, shards=2)
    assert result["cases_verified"] == 126
    assert result["shards_verified"] == 2
    assert sum(result["entity_power_counts"].values()) == 126


def test_rejects_missing_shard():
    with pytest.raises(ValueError, match="shard_count_mismatch"):
        aggregate_results(_shards(126, 7, 2)[:1], cases=126, seed=7, shards=2)


def test_rejects_duplicate_shard_index():
    results = _shards(126, 7, 2)
    results[1]["shard_index"] = 0
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_results(results, cases=126, seed=7, shards=2)


def test_rejects_tampered_entity_power_matrix():
    results = _shards(126, 7, 2)
    results[0]["entity_power_counts"]["individual|p0_minimal"] += 1
    with pytest.raises(ValueError, match="aggregate_count_mismatch|aggregate_matrix_mismatch|aggregate_strata_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)


def test_rejects_configuration_mismatch():
    results = _shards(126, 7, 2)
    results[0]["seed"] = 8
    with pytest.raises(ValueError, match="configuration_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)
