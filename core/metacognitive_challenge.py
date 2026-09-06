"""Metacognitive Challenge Layer: adaptive, evidence-bound evaluation of NORYX7 cognition."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Iterable


class ChallengeDomain(str, Enum):
    CHESS = "chess"
    MATHEMATICS = "mathematics"
    LOGIC = "logic"
    PUZZLE = "puzzle"
    NOVEL = "novel"
    MULTILINGUAL = "multilingual"


@dataclass(frozen=True)
class ChallengeSpec:
    challenge_id: str
    domain: ChallengeDomain
    difficulty: float
    prompt_digest: str
    expected_answer_digest: str
    adaptive_level: int = 0

    def __post_init__(self) -> None:
        if not self.challenge_id.strip() or len(self.challenge_id.encode()) > 256:
            raise ValueError("invalid_challenge_id")
        if not isinstance(self.domain, ChallengeDomain):
            raise TypeError("invalid_challenge_domain")
        if not isfinite(self.difficulty) or not 0.0 <= self.difficulty <= 1.0:
            raise ValueError("invalid_difficulty")
        for value, name in ((self.prompt_digest, "prompt_digest"), (self.expected_answer_digest, "expected_answer_digest")):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid_{name}")
        if isinstance(self.adaptive_level, bool) or not isinstance(self.adaptive_level, int) or not 0 <= self.adaptive_level <= 10000:
            raise ValueError("invalid_adaptive_level")


@dataclass(frozen=True)
class ChallengeTrace:
    initial_confidence: float
    final_confidence: float
    strategy: str
    intermediate_verifications: int
    errors_detected: int
    strategy_revisions: int
    answer_digest: str
    independent_verified: bool
    task_success: bool

    def __post_init__(self) -> None:
        for value, name in ((self.initial_confidence, "initial_confidence"), (self.final_confidence, "final_confidence")):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"invalid_{name}")
        if not self.strategy.strip() or len(self.strategy.encode()) > 2048:
            raise ValueError("invalid_strategy")
        for value, name in ((self.intermediate_verifications, "intermediate_verifications"), (self.errors_detected, "errors_detected"), (self.strategy_revisions, "strategy_revisions")):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10000:
                raise ValueError(f"invalid_{name}")
        if len(self.answer_digest) != 64 or any(c not in "0123456789abcdef" for c in self.answer_digest):
            raise ValueError("invalid_answer_digest")
        if not isinstance(self.independent_verified, bool) or not isinstance(self.task_success, bool):
            raise TypeError("invalid_challenge_flags")


@dataclass(frozen=True)
class ChallengeScore:
    task_performance: float
    reasoning_robustness: float
    calibration: float
    error_detection: float
    self_correction: float
    strategic_adaptation: float
    generalization: float
    long_horizon_stability: float

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("invalid_challenge_score")


class MetacognitiveChallengeEvaluator:
    """Scores only verifier-backed evidence; it never certifies improvement itself."""

    def evaluate(self, challenge: ChallengeSpec, trace: ChallengeTrace) -> ChallengeScore:
        if not isinstance(challenge, ChallengeSpec) or not isinstance(trace, ChallengeTrace):
            raise TypeError("challenge_evidence_required")
        calibration = 1.0 - abs(trace.final_confidence - float(trace.task_success))
        verification_factor = min(1.0, trace.intermediate_verifications / 3.0)
        error_factor = min(1.0, trace.errors_detected / max(1, trace.strategy_revisions + trace.errors_detected))
        correction = 1.0 if trace.task_success and trace.strategy_revisions > 0 else (0.5 if trace.task_success else 0.0)
        adaptation = min(1.0, (trace.strategy_revisions + trace.errors_detected) / 4.0)
        robustness = (verification_factor + (1.0 if trace.independent_verified else 0.0)) / 2.0
        return ChallengeScore(float(trace.task_success), robustness, calibration, error_factor, correction, adaptation, float(trace.task_success and trace.independent_verified), 1.0 if trace.intermediate_verifications >= 1 and trace.independent_verified else 0.0)


@dataclass(frozen=True)
class ImprovementEvidence:
    challenge_id: str
    baseline: ChallengeScore
    candidate: ChallengeScore
    independent_verification_digest: str


class AdaptiveChallengeController:
    """Selects harder/easier levels from verified outcomes without declaring self-improvement."""

    def next_level(self, current_level: int, score: ChallengeScore) -> int:
        if isinstance(current_level, bool) or not isinstance(current_level, int) or not 0 <= current_level <= 10000:
            raise ValueError("invalid_current_level")
        if score.task_performance >= 0.9 and score.calibration >= 0.8 and score.reasoning_robustness >= 0.8:
            return min(10000, current_level + 1)
        if score.task_performance < 0.5 or score.calibration < 0.5:
            return max(0, current_level - 1)
        return current_level

    @staticmethod
    def improvement_is_verified(evidence: ImprovementEvidence) -> bool:
        if not isinstance(evidence, ImprovementEvidence):
            raise TypeError("improvement_evidence_required")
        digest = evidence.independent_verification_digest
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid_independent_verification_digest")
        return evidence.candidate.task_performance > evidence.baseline.task_performance and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness
