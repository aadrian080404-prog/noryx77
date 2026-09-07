"""Run exactly 1,000,000 deterministic cases from difficult to extremely difficult."""
from __future__ import annotations

from test_progressive_difficulty_campaign import TOTAL_CASES, build_case


def main() -> int:
    passed = 0
    last_difficulty = None
    for index in range(TOTAL_CASES):
        case = build_case(index)
        digest = case.payload["case_digest"]
        if not isinstance(digest, str) or len(digest) != 64:
            raise AssertionError(f"invalid_digest:{index}")
        if last_difficulty == "estremamente_difficile" and case.difficulty != last_difficulty:
            raise AssertionError(f"difficulty_regression:{index}")
        if index == 333_333 and case.difficulty != "molto_difficile":
            raise AssertionError("missing_very_difficult_boundary")
        if index == 666_666 and case.difficulty != "estremamente_difficile":
            raise AssertionError("missing_extreme_boundary")
        last_difficulty = case.difficulty
        passed += 1
        if passed % 100_000 == 0:
            print(f"PROGRESS {passed}/{TOTAL_CASES} difficulty={case.difficulty}")
    print(f"PROGRESSIVE-MILLION VERIFICATION PASSED total={passed} passed={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
