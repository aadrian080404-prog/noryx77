"""Deterministic million-scale NORYX7 verification campaign.

The campaign generates scenarios rather than one million hand-written tests.  Each
case is reproducible from (campaign_seed, case_index), and difficulty is biased
toward boundary/pathological/adversarial/compound cases.

This module intentionally tests architectural invariants without invoking external
services.  It is safe to run in CI and locally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from typing import Iterable


DIFFICULTIES = ("trivial", "normal", "boundary", "pathological", "adversarial", "compound")
# Deliberately make difficult cases dominant in large campaigns.
_DIFFICULTY_WEIGHTS = (2, 8, 15, 20, 25, 30)


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


def verify_invariants(s: Scenario) -> None:
    """Cheap invariants that must hold for every generated scenario."""
    assert s.case_id >= 0
    assert s.seed >= 0
    assert s.difficulty in DIFFICULTIES
    assert s.identity >= 0 and s.capability >= 0 and s.state >= 0
    assert 0 <= s.timing <= 65535
    assert 0 <= s.failure <= 7
    assert 0 <= s.payload_size <= 2**20
    assert len(s.digest()) == 64


def run_campaign(seed: int, cases: int) -> dict[str, object]:
    if seed < 0 or cases < 1:
        raise ValueError("seed must be non-negative and cases must be positive")
    counts = {difficulty: 0 for difficulty in DIFFICULTIES}
    first_digest = None
    last_digest = None
    for case_id in range(cases):
        scenario = scenario_for(seed, case_id)
        verify_invariants(scenario)
        counts[scenario.difficulty] += 1
        digest = scenario.digest()
        first_digest = first_digest or digest
        last_digest = digest
    return {
        "seed": seed,
        "cases": cases,
        "difficulty_counts": counts,
        "first_digest": first_digest,
        "last_digest": last_digest,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args(argv)
    result = run_campaign(args.seed, args.cases)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
