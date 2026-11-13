"""Verify and aggregate every shard and marginal axis of a deterministic campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from core.scenario_matrix import (
    BEHAVIOR_CLASSES, CAPABILITY_CLASSES, ENTITY_CLASSES, IMPACT_CLASSES,
    POWER_TIERS, expected_stratum_counts,
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
    totals = {
        "difficulty_counts": {name: 0 for name in DIFFICULTIES},
        "entity_counts": {name: 0 for name in ENTITY_CLASSES},
        "power_counts": {name: 0 for name in POWER_TIERS},
        "entity_power_counts": {f"{entity}|{power}": 0 for entity in ENTITY_CLASSES for power in POWER_TIERS},
        "capability_counts": {name: 0 for name in CAPABILITY_CLASSES},
        "behavior_counts": {name: 0 for name in BEHAVIOR_CLASSES},
        "impact_counts": {name: 0 for name in IMPACT_CLASSES},
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
        if item.get("verification_scope") != "one_structural_preflight_plus_synthetic_scenario_invariants":
            raise ValueError("campaign_shard_scope_mismatch")

        for key, target in totals.items():
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
    for key, counts in totals.items():
        if sum(counts.values()) != cases:
            raise ValueError(f"campaign_aggregate_{key}_count_mismatch")

    expected_matrix = {
        f"{entity}|{power}": count
        for (entity, power), count in expected_stratum_counts(cases, seed=seed).items()
    }
    if totals["entity_power_counts"] != expected_matrix:
        raise ValueError("campaign_aggregate_strata_mismatch")

    return {
        "seed": seed,
        "cases_requested": cases,
        "cases_verified": total_executed,
        "shards_verified": len(seen),
        **totals,
        "coverage_axes": ["entity", "power", "difficulty", "capability", "behavior", "impact"],
        "verification_scope": "one_structural_preflight_per_shard_plus_synthetic_scenario_invariants",
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
