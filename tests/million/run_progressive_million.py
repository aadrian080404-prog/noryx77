"""Run exactly 1,000,000 deterministic cases from difficult to extremely difficult."""
from __future__ import annotations

from tests.million.test_progressive_difficulty_campaign import TOTAL_CASES, build_case, verify_case


def main() -> int:
    passed = 0
    previous_rank = -1
    rank = {"difficile": 0, "molto_difficile": 1, "estremamente_difficile": 2}
    for index in range(TOTAL_CASES):
        case = build_case(index)
        verify_case(case)
        current_rank = rank.get(case.difficulty)
        if current_rank is None or current_rank < previous_rank:
            raise AssertionError(f"difficulty_regression:{index}")
        previous_rank = current_rank
        if index == 333_333 and case.difficulty != "molto_difficile":
            raise AssertionError("missing_very_difficult_boundary")
        if index == 666_666 and case.difficulty != "estremamente_difficile":
            raise AssertionError("missing_extreme_boundary")
        passed += 1
        if passed % 100_000 == 0:
            print(f"PROGRESS {passed}/{TOTAL_CASES} difficulty={case.difficulty}")
    print(f"PROGRESSIVE-MILLION VERIFICATION PASSED total={passed} passed={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
