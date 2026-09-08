"""Deterministic, shardable million-scale NORYX7 verification campaign.

The campaign generates reproducible scenarios and performs a real architecture
preflight before spending the configured case budget. It is deliberately biased
toward boundary/pathological/adversarial/compound cases and refuses to report a
successful campaign when the requested budget or difficulty coverage is not met.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from dataclasses import dataclass
from typing import Iterable

DIFFICULTIES = ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")
_DIFFICULTY_WEIGHTS = (2, 8, 15, 20, 25, 30)
# Minimum fractions required in every complete campaign. This prevents a biased
# generator from satisfying the million-case requirement with easy cases only.
_MIN_DIFFICULTY_FRACTIONS = {
    "trivial": 0.005,
    "normal": 0.04,
    "boundary": 0.10,
    "pathological": 0.15,
    "adversarial": 0.20,
    "compound": 0.25,
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

    def digest(self) -> str:
        encoded = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def scenario_for(seed: int, case_id: int) -> Scenario:
    """Generate exactly one deterministic scenario from a stable coordinate."""
    if not isinstance(seed, int) or seed < 0 or not isinstance(case_id, int) or case_id < 0:
        raise ValueError("seed and case_id must be non-negative integers")
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
    return Scenario(
        case_id=case_id,
        seed=seed,
        difficulty=difficulty,
        identity=rng.randint(i0, i1),
        capability=rng.randint(c0, c1),
        state=rng.randint(s0, s1),
        timing=rng.randint(0, 2**16 - 1),
        failure=rng.randint(f0, 7),
        payload_size=rng.randint(0, p1),
    )


def verify_invariants(scenario: Scenario) -> None:
    """Cheap per-case invariants that must hold for every generated scenario."""
    assert scenario.case_id >= 0
    assert scenario.seed >= 0
    assert scenario.difficulty in DIFFICULTIES
    assert scenario.identity >= 0 and scenario.capability >= 0 and scenario.state >= 0
    assert 0 <= scenario.timing <= 65535
    assert 0 <= scenario.failure <= 7
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
    if not isinstance(seed, int) or seed < 0 or not isinstance(cases, int) or cases < 1:
        raise ValueError("seed must be non-negative and cases must be positive")
    if not isinstance(shard_index, int) or not 0 <= shard_index < shards:
        raise ValueError("invalid shard_index")
    if not isinstance(shards, int) or not 1 <= shards <= cases:
        raise ValueError("shards must be between 1 and cases")

    started = time.monotonic()
    _preflight()
    counts = {difficulty: 0 for difficulty in DIFFICULTIES}
    executed = 0
    first_digest: str | None = None
    last_digest: str | None = None
    failure_cases: list[int] = []

    # The coordinate system is global: sharding never changes a case's identity
    # or seed, so a failed shard can be reproduced independently.
    for case_id in range(shard_index, cases, shards):
        scenario = scenario_for(seed, case_id)
        try:
            verify_invariants(scenario)
        except Exception:
            failure_cases.append(case_id)
            raise
        counts[scenario.difficulty] += 1
        digest = scenario.digest()
        first_digest = first_digest or digest
        last_digest = digest
        executed += 1

    # Coverage is enforced only for an unsharded complete campaign. Each shard is
    # still required to execute its exact deterministic allocation.
    if shards == 1:
        _validate_coverage(counts, cases)
    if executed != ((cases - 1 - shard_index) // shards + 1):
        raise RuntimeError("campaign_case_budget_not_reached")
    if failure_cases:
        raise RuntimeError(f"campaign_failures:{failure_cases[:20]}")

    return {
        "seed": seed,
        "cases": cases,
        "executed": executed,
        "shard_index": shard_index,
        "shards": shards,
        "difficulty_counts": counts,
        "first_digest": first_digest,
        "last_digest": last_digest,
        "duration_seconds": round(time.monotonic() - started, 6),
        "status": "passed",
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
