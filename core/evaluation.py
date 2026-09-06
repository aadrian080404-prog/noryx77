"""Bounded evaluation matrix for continuous NORYX7 verification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class EvaluationDimension(str, Enum):
    TECHNICAL = "technical"
    COGNITIVE = "cognitive"
    METACOGNITIVE = "metacognitive"
    ADVERSARIAL = "adversarial"
    SAFETY = "safety"
    SECURITY = "security"
    RECOVERY = "recovery"
    RESOURCE = "resource"
    UNCERTAINTY = "uncertainty"
    HUMAN = "human"
    REGRESSION = "regression"


@dataclass(frozen=True)
class EvaluationResult:
    dimension: EvaluationDimension
    passed: bool
    score: float
    evidence: str


class EvaluationMatrix:
    """Aggregates independent results; no single dimension can hide a failure."""

    def __init__(self) -> None:
        self._results: list[EvaluationResult] = []

    def record(self, result: EvaluationResult) -> None:
        if not isinstance(result, EvaluationResult):
            raise TypeError("evaluation_result_required")
        if not isinstance(result.dimension, EvaluationDimension):
            raise TypeError("invalid_evaluation_dimension")
        if not isinstance(result.passed, bool):
            raise TypeError("invalid_pass_flag")
        if not isfinite(result.score) or not 0.0 <= result.score <= 1.0:
            raise ValueError("invalid_score")
        if not isinstance(result.evidence, str) or not result.evidence.strip():
            raise ValueError("evidence_required")
        self._results.append(result)

    def results(self) -> tuple[EvaluationResult, ...]:
        return tuple(self._results)

    def passed(self) -> bool:
        return bool(self._results) and all(result.passed for result in self._results)

    def failed_dimensions(self) -> tuple[EvaluationDimension, ...]:
        return tuple(dict.fromkeys(result.dimension for result in self._results if not result.passed))
