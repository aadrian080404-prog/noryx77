"""Deterministic one-million-case campaign ordered by difficulty.

The campaign is intentionally difficulty-driven rather than category-balanced:
Difficile -> Molto difficile -> Estremamente difficile.
The frozen baseline is not modified by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

TOTAL_CASES = 1_000_000
DIFFICULTY_BUCKETS = (
    ("difficile", 333_333),
    ("molto_difficile", 333_333),
    ("estremamente_difficile", 333_334),
)
SEED = 524525373703


@dataclass(frozen=True)
class CampaignCase:
    index: int
    difficulty: str
    payload: dict[str, object]


def _digest(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def build_case(index: int) -> CampaignCase:
    if not 0 <= index < TOTAL_CASES:
        raise ValueError("invalid_case_index")
    cursor = 0
    for difficulty, count in DIFFICULTY_BUCKETS:
        if index < cursor + count:
            local = index - cursor
            payload = {
                "seed": SEED,
                "case": index,
                "local_case": local,
                "difficulty": difficulty,
                "nested_depth": 2 if difficulty == "difficile" else 6 if difficulty == "molto_difficile" else 12,
                "mutation_rounds": 1 if difficulty == "difficile" else 4 if difficulty == "molto_difficile" else 8,
                "replay_attempts": 1 if difficulty == "difficile" else 3 if difficulty == "molto_difficile" else 7,
            }
            payload["case_digest"] = _digest(payload)
            return CampaignCase(index=index, difficulty=difficulty, payload=payload)
        cursor += count
    raise AssertionError("difficulty_partition_error")


def verify_partition() -> None:
    assert sum(count for _, count in DIFFICULTY_BUCKETS) == TOTAL_CASES
    assert DIFFICULTY_BUCKETS[0][0] == "difficile"
    assert DIFFICULTY_BUCKETS[-1][0] == "estremamente_difficile"
    assert build_case(0).difficulty == "difficile"
    assert build_case(333_333).difficulty == "molto_difficile"
    assert build_case(666_666).difficulty == "estremamente_difficile"
    assert build_case(999_999).difficulty == "estremamente_difficile"


def test_progressive_campaign_partition() -> None:
    verify_partition()


def test_progressive_campaign_is_deterministic() -> None:
    samples = (0, 1, 333_332, 333_333, 666_665, 666_666, 999_998, 999_999)
    assert [build_case(i) for i in samples] == [build_case(i) for i in samples]
