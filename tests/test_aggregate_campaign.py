from __future__ import annotations

import pytest

from core.scenario_matrix import (
    ENTITY_CLASSES, POWER_TIERS, CAPABILITY_CLASSES, BEHAVIOR_CLASSES,
    IMPACT_CLASSES,
)
from tests.million_scale_campaign import scenario_for
from tests.aggregate_campaign import aggregate_results


def _shards(cases: int, seed: int, shards: int):
    results = []
    for shard_index in range(shards):
        difficulty = {name: 0 for name in ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")}
        entities = {name: 0 for name in ENTITY_CLASSES}
        powers = {name: 0 for name in POWER_TIERS}
        matrix = {f"{entity}|{power}": 0 for entity in ENTITY_CLASSES for power in POWER_TIERS}
        capabilities = {name: 0 for name in CAPABILITY_CLASSES}
        behaviors = {name: 0 for name in BEHAVIOR_CLASSES}
        impacts = {name: 0 for name in IMPACT_CLASSES}
        full_matrix = {
            f"{entity}|{power}|{capability}|{behavior}|{impact}": 0
            for entity in ENTITY_CLASSES
            for power in POWER_TIERS
            for capability in CAPABILITY_CLASSES
            for behavior in BEHAVIOR_CLASSES
            for impact in IMPACT_CLASSES
        }
        executed = 0
        for case_id in range(shard_index, cases, shards):
            scenario = scenario_for(seed, case_id)
            difficulty[scenario.difficulty] += 1
            entities[scenario.entity_class] += 1
            powers[scenario.power_tier] += 1
            matrix[f"{scenario.entity_class}|{scenario.power_tier}"] += 1
            capabilities[scenario.capability_class] += 1
            behaviors[scenario.behavior_class] += 1
            impacts[scenario.impact_class] += 1
            full_matrix[
                f"{scenario.entity_class}|{scenario.power_tier}|{scenario.capability_class}|"
                f"{scenario.behavior_class}|{scenario.impact_class}"
            ] += 1
            executed += 1
        results.append({
            "seed": seed, "cases": cases, "executed": executed,
            "shard_index": shard_index, "shards": shards,
            "difficulty_counts": difficulty, "entity_counts": entities,
            "power_counts": powers, "entity_power_counts": matrix,
            "capability_counts": capabilities, "behavior_counts": behaviors,
            "impact_counts": impacts, "full_matrix_counts": full_matrix,
            "verification_scope": "one_structural_preflight_plus_synthetic_invariants_across_entity_power_capability_behavior_impact",
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


def test_aggregates_all_five_dimensions_and_full_matrix():
    result = aggregate_results(_shards(126, 7, 2), cases=126, seed=7, shards=2)
    assert sum(result["capability_counts"].values()) == 126
    assert sum(result["behavior_counts"].values()) == 126
    assert sum(result["impact_counts"].values()) == 126
    assert sum(result["full_matrix_counts"].values()) == 126
    assert len(result["full_matrix_counts"]) == (
        len(ENTITY_CLASSES) * len(POWER_TIERS) * len(CAPABILITY_CLASSES)
        * len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES)
    )


def test_rejects_tampered_full_matrix_cell():
    results = _shards(126, 7, 2)
    first_key = next(iter(results[0]["full_matrix_counts"]))
    results[0]["full_matrix_counts"][first_key] += 1
    with pytest.raises(ValueError, match="aggregate_matrix_mismatch|aggregate_strata_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)


def test_rejects_missing_capability_axis():
    results = _shards(126, 7, 2)
    results[0]["capability_counts"].pop(next(iter(results[0]["capability_counts"])))
    with pytest.raises(ValueError, match="capability_counts_schema_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)
