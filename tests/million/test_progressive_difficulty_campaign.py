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


def _difficulty_parameters(difficulty: str) -> tuple[int, int, int, int]:
    if difficulty == "difficile":
        return (2, 1, 1, 4)
    if difficulty == "molto_difficile":
        return (6, 4, 3, 16)
    if difficulty == "estremamente_difficile":
        return (12, 8, 7, 64)
    raise AssertionError("unknown_difficulty")


def build_case(index: int) -> CampaignCase:
    if not 0 <= index < TOTAL_CASES:
        raise ValueError("invalid_case_index")
    cursor = 0
    for difficulty, count in DIFFICULTY_BUCKETS:
        if index < cursor + count:
            local = index - cursor
            nested_depth, mutation_rounds, replay_attempts, operation_count = _difficulty_parameters(difficulty)
            payload: dict[str, object] = {
                "seed": SEED,
                "case": index,
                "local_case": local,
                "difficulty": difficulty,
                "nested_depth": nested_depth,
                "mutation_rounds": mutation_rounds,
                "replay_attempts": replay_attempts,
                "operation_count": operation_count,
                "adversarial": {
                    "unicode": local % 7 == 0,
                    "boundary_lengths": local % 11 == 0,
                    "duplicate_replay": local % 5 == 0,
                    "epoch_transition": local % 13 == 0,
                    "device_mismatch": local % 17 == 0,
                    "capability_expiry": local % 19 == 0,
                },
            }
            payload["case_digest"] = _digest(payload)
            return CampaignCase(index=index, difficulty=difficulty, payload=payload)
        cursor += count
    raise AssertionError("difficulty_partition_error")


def verify_case(case: CampaignCase) -> None:
    payload = case.payload
    assert payload["seed"] == SEED
    assert payload["case"] == case.index
    assert payload["difficulty"] == case.difficulty
    assert isinstance(payload["case_digest"], str)
    assert len(payload["case_digest"]) == 64
    assert payload["case_digest"] == _digest({k: v for k, v in payload.items() if k != "case_digest"})
    depth, mutations, replays, operations = _difficulty_parameters(case.difficulty)
    assert payload["nested_depth"] == depth
    assert payload["mutation_rounds"] == mutations
    assert payload["replay_attempts"] == replays
    assert payload["operation_count"] == operations


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


def test_progressive_campaign_case_oracle() -> None:
    for index in (0, 333_332, 333_333, 666_665, 666_666, 999_999):
        verify_case(build_case(index))
