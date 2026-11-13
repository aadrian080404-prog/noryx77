"""Deterministic, shardable generated-scenario verification campaign.

Synthetic scenario invariants are reported separately from live runtime or
production attack/defence evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from math import gcd
import time
from dataclasses import dataclass
from typing import Iterable

from core.scenario_matrix import (
    BEHAVIOR_CLASSES, CAPABILITY_CLASSES, ENTITY_CLASSES, IMPACT_CLASSES,
    POWER_TIERS, coordinate_for,
)

DIFFICULTIES = ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")
_DIFFICULTY_WEIGHTS = (2, 8, 15, 20, 25, 30)
MAX_CAMPAIGN_CASES = 10_000_000
MAX_SEED = 2**63 - 1
VERIFICATION_SCOPE = "one_structural_preflight_plus_synthetic_scenario_invariants"
_MIN_DIFFICULTY_FRACTIONS = {
    "trivial": 0.005, "normal": 0.04, "boundary": 0.10,
    "pathological": 0.15, "adversarial": 0.20, "compound": 0.25,
}


@dataclass(frozen=True)
class Scenario:
    case_id: int
    seed: int
    difficulty: str
    identity: int
    capability: int
    state: int
    timing: int
    failure: int
    payload_size: int
    entity_class: str
    power_tier: str
    capability_class: str
    behavior_class: str
    impact_class: str

    def digest(self) -> str:
        encoded = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def scenario_for(seed: int, case_id: int) -> Scenario:
    """Generate exactly one deterministic scenario from a stable coordinate."""
    if (
        isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED
        or isinstance(case_id, bool) or not isinstance(case_id, int) or case_id < 0
    ):
        raise ValueError("seed and case_id must be valid non-negative integers")
    rng = random.Random((seed << 32) ^ case_id)
    difficulty = rng.choices(DIFFICULTIES, weights=_DIFFICULTY_WEIGHTS, k=1)[0]
    ranges = {
        "trivial": (1, 4, 1, 4, 1, 2, 0, 64),
        "normal": (1, 32, 1, 32, 1, 16, 0, 4096),
        "boundary": (0, 1024, 0, 1024, 0, 64, 0, 65536),
        "pathological": (0, 65535, 0, 65535, 0, 255, 0, 1048576),
        "adversarial": (0, 65535, 0, 65535, 0, 255, 1, 1048576),
        "compound": (0, 2**31 - 1, 0, 2**31 - 1, 0, 2**16 - 1, 0, 2**20),
    }[difficulty]
    i0, i1, c0, c1, s0, s1, f0, p1 = ranges
    coordinate = coordinate_for(seed, case_id)
    return Scenario(
        case_id=case_id, seed=seed, difficulty=difficulty,
        identity=rng.randint(i0, i1), capability=rng.randint(c0, c1),
        state=rng.randint(s0, s1), timing=rng.randint(0, 2**16 - 1),
        failure=rng.randint(f0, 7), payload_size=rng.randint(0, p1),
        entity_class=coordinate.entity_class, power_tier=coordinate.power_tier,
        capability_class=coordinate.capability_class,
        behavior_class=coordinate.behavior_class, impact_class=coordinate.impact_class,
    )


def verify_invariants(scenario: Scenario) -> None:
    """Cheap per-case invariants that must hold for every generated scenario."""
    assert scenario.case_id >= 0 and scenario.seed >= 0
    assert scenario.difficulty in DIFFICULTIES
    assert scenario.entity_class in ENTITY_CLASSES and scenario.power_tier in POWER_TIERS
    assert scenario.capability_class in CAPABILITY_CLASSES
    assert scenario.behavior_class in BEHAVIOR_CLASSES
    assert scenario.impact_class in IMPACT_CLASSES
    assert scenario.identity >= 0 and scenario.capability >= 0 and scenario.state >= 0
    assert 0 <= scenario.timing <= 65535 and 0 <= scenario.failure <= 7
    assert 0 <= scenario.payload_size <= 2**20
    assert len(scenario.digest()) == 64


def _preflight() -> None:
    """Run the real structural gates before accepting generated-case evidence."""
    from ecosystem.completeness import require_complete
    require_complete()


def _validate_coverage(counts: dict[str, int], cases: int) -> None:
    missing = {
        difficulty: minimum
        for difficulty, fraction in _MIN_DIFFICULTY_FRACTIONS.items()
        if (minimum := max(1, int(cases * fraction))) > counts.get(difficulty, 0)
    }
    if missing:
        raise RuntimeError(f"difficulty_coverage_failed:{missing}")


def run_campaign(seed: int, cases: int, *, shard_index: int = 0, shards: int = 1) -> dict[str, object]:
    if (
        isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED
        or isinstance(cases, bool) or not isinstance(cases, int) or not 1 <= cases <= MAX_CAMPAIGN_CASES
    ):
        raise ValueError("seed must be bounded and cases must be between 1 and 10000000")
    if isinstance(shards, bool) or not isinstance(shards, int) or not 1 <= shards <= cases:
        raise ValueError("shards must be between 1 and cases")
    if isinstance(shard_index, bool) or not isinstance(shard_index, int) or not 0 <= shard_index < shards:
        raise ValueError("invalid shard_index")
    if gcd(shards, len(ENTITY_CLASSES) * len(POWER_TIERS)) != 1:
        raise ValueError("shard_count_must_be_coprime_with_strata")

    started = time.monotonic()
    _preflight()
    counts = {name: 0 for name in DIFFICULTIES}
    entity_counts = {name: 0 for name in ENTITY_CLASSES}
    power_counts = {name: 0 for name in POWER_TIERS}
    capability_counts = {name: 0 for name in CAPABILITY_CLASSES}
    behavior_counts = {name: 0 for name in BEHAVIOR_CLASSES}
    impact_counts = {name: 0 for name in IMPACT_CLASSES}
    entity_power_counts = {f"{entity}|{power}": 0 for entity in ENTITY_CLASSES for power in POWER_TIERS}
    executed = 0
    first_digest: str | None = None
    last_digest: str | None = None

    for case_id in range(shard_index, cases, shards):
        scenario = scenario_for(seed, case_id)
        verify_invariants(scenario)
        counts[scenario.difficulty] += 1
        entity_counts[scenario.entity_class] += 1
        power_counts[scenario.power_tier] += 1
        capability_counts[scenario.capability_class] += 1
        behavior_counts[scenario.behavior_class] += 1
        impact_counts[scenario.impact_class] += 1
        entity_power_counts[f"{scenario.entity_class}|{scenario.power_tier}"] += 1
        digest = scenario.digest()
        first_digest = first_digest or digest
        last_digest = digest
        executed += 1

    _validate_coverage(counts, executed)
    expected = (cases - 1 - shard_index) // shards + 1
    if executed != expected:
        raise RuntimeError("campaign_case_budget_not_reached")

    return {
        "seed": seed, "cases": cases, "executed": executed,
        "shard_index": shard_index, "shards": shards,
        "difficulty_counts": counts, "entity_counts": entity_counts,
        "power_counts": power_counts, "entity_power_counts": entity_power_counts,
        "capability_counts": capability_counts, "behavior_counts": behavior_counts,
        "impact_counts": impact_counts,
        "first_digest": first_digest, "last_digest": last_digest,
        "verification_scope": VERIFICATION_SCOPE,
        "duration_seconds": round(time.monotonic() - started, 6), "status": "passed",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args(argv)
    result = run_campaign(args.seed, args.cases, shard_index=args.shard_index, shards=args.shards)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
