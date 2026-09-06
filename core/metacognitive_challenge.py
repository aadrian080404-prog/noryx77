"""Metacognitive Challenge Layer: adaptive, evidence-bound evaluation of NORYX7 cognition."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import isfinite
from typing import Callable


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
        if not isinstance(self.challenge_id, str) or not self.challenge_id.strip() or len(self.challenge_id.encode()) > 256:
            raise ValueError("invalid_challenge_id")
        if not isinstance(self.domain, ChallengeDomain):
            raise TypeError("invalid_challenge_domain")
        if not isfinite(self.difficulty) or not 0.0 <= self.difficulty <= 1.0:
            raise ValueError("invalid_difficulty")
        for value, name in ((self.prompt_digest, "prompt_digest"), (self.expected_answer_digest, "expected_answer_digest")):
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
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
        if not isinstance(self.strategy, str) or not self.strategy.strip() or len(self.strategy.encode()) > 2048:
            raise ValueError("invalid_strategy")
        for value, name in ((self.intermediate_verifications, "intermediate_verifications"), (self.errors_detected, "errors_detected"), (self.strategy_revisions, "strategy_revisions")):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10000:
                raise ValueError(f"invalid_{name}")
        if not isinstance(self.answer_digest, str) or len(self.answer_digest) != 64 or any(c not in "0123456789abcdef" for c in self.answer_digest):
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


@dataclass(frozen=True)
class ChallengeVerification:
    challenge_id: str
    answer_matches: bool
    independent_verified: bool
    evidence_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.challenge_id, str) or not self.challenge_id.strip() or len(self.challenge_id.encode()) > 256:
            raise ValueError("invalid_challenge_id")
        if not isinstance(self.answer_matches, bool) or not isinstance(self.independent_verified, bool):
            raise TypeError("invalid_verification_flags")
        if not isinstance(self.evidence_digest, str) or len(self.evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in self.evidence_digest):
            raise ValueError("invalid_evidence_digest")


class IndependentChallengeVerifier:
    """Independent boundary: correctness is certified by an injected verifier, never by trace self-assertion."""

    def __init__(self, verifier: Callable[[ChallengeSpec, ChallengeTrace], bool]):
        if not callable(verifier):
            raise TypeError("independent_verifier_required")
        self._verifier = verifier

    def verify(self, challenge: ChallengeSpec, trace: ChallengeTrace) -> ChallengeVerification:
        if not isinstance(challenge, ChallengeSpec) or not isinstance(trace, ChallengeTrace):
            raise TypeError("challenge_evidence_required")
        try:
            independent_verified = self._verifier(challenge, trace) is True
        except Exception:
            independent_verified = False
        answer_matches = trace.answer_digest == challenge.expected_answer_digest
        payload = "|".join((challenge.challenge_id, challenge.prompt_digest, challenge.expected_answer_digest,
                            trace.answer_digest, str(answer_matches), str(independent_verified), str(trace.task_success))).encode("utf-8")
        return ChallengeVerification(
            challenge.challenge_id,
            answer_matches,
            independent_verified,
            sha256(payload).hexdigest(),
        )


class MetacognitiveChallengeEvaluator:
    """Scores only verifier-backed evidence; it never certifies improvement itself."""

    def evaluate(self, challenge: ChallengeSpec, trace: ChallengeTrace, verification: ChallengeVerification) -> ChallengeScore:
        if not isinstance(challenge, ChallengeSpec) or not isinstance(trace, ChallengeTrace):
            raise TypeError("challenge_evidence_required")
        if not isinstance(verification, ChallengeVerification) or verification.challenge_id != challenge.challenge_id:
            raise ValueError("independent_verification_required")
        task_success = bool(verification.answer_matches and verification.independent_verified and trace.task_success)
        calibration = 1.0 - abs(trace.final_confidence - float(task_success))
        verification_factor = min(1.0, trace.intermediate_verifications / 3.0)
        error_factor = min(1.0, trace.errors_detected / max(1, trace.strategy_revisions + trace.errors_detected))
        correction = 1.0 if task_success and trace.strategy_revisions > 0 else (0.5 if task_success else 0.0)
        adaptation = min(1.0, (trace.strategy_revisions + trace.errors_detected) / 4.0)
        robustness = (verification_factor + (1.0 if verification.independent_verified else 0.0)) / 2.0
        return ChallengeScore(float(task_success), robustness, calibration, error_factor, correction, adaptation,
                              float(task_success and verification.independent_verified),
                              1.0 if trace.intermediate_verifications >= 1 and verification.independent_verified else 0.0)


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
        if not isinstance(score, ChallengeScore):
            raise TypeError("challenge_score_required")
        if score.task_performance >= 0.9 and score.calibration >= 0.8 and score.reasoning_robustness >= 0.8:
            return min(10000, current_level + 1)
        if score.task_performance < 0.5 or score.calibration < 0.5:
            return max(0, current_level - 1)
        return current_level

    @staticmethod
    def improvement_is_verified(evidence: ImprovementEvidence, verifier: Callable[[ImprovementEvidence], bool]) -> bool:
        if not isinstance(evidence, ImprovementEvidence):
            raise TypeError("improvement_evidence_required")
        if not callable(verifier):
            raise TypeError("independent_verifier_required")
        digest = evidence.independent_verification_digest
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid_independent_verification_digest")
        try:
            if verifier(evidence) is not True:
                return False
        except Exception:
            return False
        return evidence.candidate.task_performance > evidence.baseline.task_performance and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness
