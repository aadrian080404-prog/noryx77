"""Verify and aggregate all deterministic shards of a generated-scenario campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from core.scenario_matrix import (
    ENTITY_CLASSES, POWER_TIERS, CAPABILITY_CLASSES, BEHAVIOR_CLASSES,
    IMPACT_CLASSES, expected_stratum_counts,
)

DIFFICULTIES = ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")


def aggregate_results(results: Iterable[dict[str, object]], *, cases: int, seed: int, shards: int) -> dict[str, object]:
    if isinstance(cases, bool) or not isinstance(cases, int) or not 1 <= cases <= 10_000_000:
        raise ValueError("invalid_expected_case_count")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_expected_seed")
    if isinstance(shards, bool) or not isinstance(shards, int) or not 1 <= shards <= cases:
        raise ValueError("invalid_expected_shard_count")

    items = list(results)
    if len(items) != shards:
        raise ValueError("campaign_shard_count_mismatch")

    seen: set[int] = set()
    difficulty = {name: 0 for name in DIFFICULTIES}
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
    total_executed = 0

    for item in items:
        if not isinstance(item, dict) or item.get("status") != "passed":
            raise ValueError("campaign_shard_not_passed")
        if item.get("seed") != seed or item.get("cases") != cases or item.get("shards") != shards:
            raise ValueError("campaign_shard_configuration_mismatch")
        index = item.get("shard_index")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < shards or index in seen:
            raise ValueError("campaign_shard_index_invalid_or_duplicate")
        seen.add(index)
        expected_executed = (cases - 1 - index) // shards + 1
        if item.get("executed") != expected_executed:
            raise ValueError("campaign_shard_execution_count_mismatch")
        if item.get("verification_scope") != "one_structural_preflight_plus_synthetic_invariants_across_entity_power_capability_behavior_impact":
            raise ValueError("campaign_shard_scope_mismatch")

        for target, key in (
            (difficulty, "difficulty_counts"),
            (entities, "entity_counts"),
            (powers, "power_counts"),
            (matrix, "entity_power_counts"),
            (capabilities, "capability_counts"),
            (behaviors, "behavior_counts"),
            (impacts, "impact_counts"),
            (full_matrix, "full_matrix_counts"),
        ):
            counts = item.get(key)
            if not isinstance(counts, dict) or set(counts) != set(target):
                raise ValueError(f"campaign_shard_{key}_schema_mismatch")
            for name, value in counts.items():
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"campaign_shard_{key}_invalid_count")
                target[name] += value
        total_executed += expected_executed

    if seen != set(range(shards)) or total_executed != cases:
        raise ValueError("campaign_shards_do_not_cover_requested_range")
    if sum(difficulty.values()) != cases or sum(entities.values()) != cases:
        raise ValueError("campaign_aggregate_count_mismatch")
    if (
        sum(powers.values()) != cases
        or sum(matrix.values()) != cases
        or sum(capabilities.values()) != cases
        or sum(behaviors.values()) != cases
        or sum(impacts.values()) != cases
        or sum(full_matrix.values()) != cases
    ):
        raise ValueError("campaign_aggregate_matrix_mismatch")

    expected_strata = expected_stratum_counts(cases, seed=seed)
    expected_full_matrix = {
        "|".join(key): count for key, count in expected_strata.items()
    }
    if full_matrix != expected_full_matrix:
        raise ValueError("campaign_aggregate_strata_mismatch")

    expected_entity_power = {
        f"{entity}|{power}": 0
        for entity in ENTITY_CLASSES
        for power in POWER_TIERS
    }
    for (entity_key, power_key, _, _, _), count in expected_strata.items():
        expected_entity_power[f"{entity_key}|{power_key}"] += count
    if matrix != expected_entity_power:
        raise ValueError("campaign_aggregate_entity_power_mismatch")

    return {
        "seed": seed,
        "cases_requested": cases,
        "cases_verified": total_executed,
        "shards_verified": len(seen),
        "difficulty_counts": difficulty,
        "entity_counts": entities,
        "power_counts": powers,
        "entity_power_counts": matrix,
        "capability_counts": capabilities,
        "behavior_counts": behaviors,
        "impact_counts": impacts,
        "full_matrix_counts": full_matrix,
        "verification_scope": "one_structural_preflight_per_shard_plus_synthetic_invariants_across_entity_power_capability_behavior_impact",
        "status": "passed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--cases", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--shards", required=True, type=int)
    parser.add_argument("--output", default="generated-scenario-aggregate.json")
    args = parser.parse_args(argv)

    paths = sorted(Path(args.artifacts_dir).glob("generated-scenario-result-*.json"))
    if len(paths) != args.shards:
        raise ValueError("campaign_artifact_count_mismatch")
    results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    aggregate = aggregate_results(results, cases=args.cases, seed=args.seed, shards=args.shards)
    Path(args.output).write_text(json.dumps(aggregate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
