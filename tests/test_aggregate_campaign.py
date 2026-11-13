from __future__ import annotations

import pytest

from core.scenario_matrix import (
    BEHAVIOR_CLASSES, CAPABILITY_CLASSES, ENTITY_CLASSES, IMPACT_CLASSES, POWER_TIERS,
)
from tests.million_scale_campaign import scenario_for
from tests.aggregate_campaign import aggregate_results


def _shards(cases: int, seed: int, shards: int):
    results = []
    for shard_index in range(shards):
        axes = {
            "difficulty_counts": {name: 0 for name in ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")},
            "entity_counts": {name: 0 for name in ENTITY_CLASSES},
            "power_counts": {name: 0 for name in POWER_TIERS},
            "entity_power_counts": {f"{entity}|{power}": 0 for entity in ENTITY_CLASSES for power in POWER_TIERS},
            "capability_counts": {name: 0 for name in CAPABILITY_CLASSES},
            "behavior_counts": {name: 0 for name in BEHAVIOR_CLASSES},
            "impact_counts": {name: 0 for name in IMPACT_CLASSES},
            "entity_behavior_counts": {f"{entity}|{behavior}": 0 for entity in ENTITY_CLASSES for behavior in BEHAVIOR_CLASSES},
            "entity_impact_counts": {f"{entity}|{impact}": 0 for entity in ENTITY_CLASSES for impact in IMPACT_CLASSES},
            "power_capability_counts": {f"{power}|{capability}": 0 for power in POWER_TIERS for capability in CAPABILITY_CLASSES},
            "capability_impact_counts": {f"{capability}|{impact}": 0 for capability in CAPABILITY_CLASSES for impact in IMPACT_CLASSES},
            "behavior_impact_counts": {f"{behavior}|{impact}": 0 for behavior in BEHAVIOR_CLASSES for impact in IMPACT_CLASSES},
        }
        executed = 0
        for case_id in range(shard_index, cases, shards):
            scenario = scenario_for(seed, case_id)
            axes["difficulty_counts"][scenario.difficulty] += 1
            axes["entity_counts"][scenario.entity_class] += 1
            axes["power_counts"][scenario.power_tier] += 1
            axes["entity_power_counts"][f"{scenario.entity_class}|{scenario.power_tier}"] += 1
            axes["capability_counts"][scenario.capability_class] += 1
            axes["behavior_counts"][scenario.behavior_class] += 1
            axes["impact_counts"][scenario.impact_class] += 1
            axes["entity_behavior_counts"][f"{scenario.entity_class}|{scenario.behavior_class}"] += 1
            axes["entity_impact_counts"][f"{scenario.entity_class}|{scenario.impact_class}"] += 1
            axes["power_capability_counts"][f"{scenario.power_tier}|{scenario.capability_class}"] += 1
            axes["capability_impact_counts"][f"{scenario.capability_class}|{scenario.impact_class}"] += 1
            axes["behavior_impact_counts"][f"{scenario.behavior_class}|{scenario.impact_class}"] += 1
            executed += 1
        results.append({
            "seed": seed, "cases": cases, "executed": executed,
            "shard_index": shard_index, "shards": shards, **axes,
            "verification_scope": "one_structural_preflight_plus_synthetic_scenario_invariants",
            "status": "passed",
        })
    return results


def test_aggregates_all_shards_and_exact_strata():
    result = aggregate_results(_shards(126, 7, 2), cases=126, seed=7, shards=2)
    assert result["cases_verified"] == 126
    assert result["shards_verified"] == 2
    assert sum(result["entity_power_counts"].values()) == 126
    assert result["coverage_axes"] == ["entity", "power", "difficulty", "capability", "behavior", "impact"]
    assert len(result["entity_behavior_counts"]) == 9 * 8
    assert len(result["entity_impact_counts"]) == 9 * 6
    assert len(result["power_capability_counts"]) == 7 * 8
    assert len(result["capability_impact_counts"]) == 8 * 6
    assert len(result["behavior_impact_counts"]) == 8 * 6
    for key in ("entity_behavior_counts", "entity_impact_counts", "power_capability_counts", "capability_impact_counts", "behavior_impact_counts"):
        assert sum(result[key].values()) == 126


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
    with pytest.raises(ValueError, match="aggregate_entity_power_counts_count_mismatch|strata_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)


def test_rejects_tampered_behavior_axis():
    results = _shards(126, 7, 2)
    results[0]["behavior_counts"]["benign"] += 1
    with pytest.raises(ValueError, match="aggregate_behavior_counts_count_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)


def test_rejects_configuration_mismatch():
    results = _shards(126, 7, 2)
    results[0]["seed"] = 8
    with pytest.raises(ValueError, match="configuration_mismatch"):
        aggregate_results(results, cases=126, seed=7, shards=2)
