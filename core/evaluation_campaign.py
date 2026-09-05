"""Deterministic, bounded evaluation-campaign orchestration.

The campaign layer generates local test cases only. It never executes an
attack, contacts an external target, or grants runtime authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .adversarial import AdversarialEngine, AttackScenario, MAX_SCENARIOS
from .evaluation import EvaluationDimension, EvaluationMatrix, EvaluationResult


@dataclass(frozen=True)
class CampaignManifest:
    campaign_id: str
    seed: int
    cases: int
    holdout_cases: int
    training_cases: int


class EvaluationCampaign:
    """Builds reproducible generated-case and holdout manifests."""

    def __init__(self, *, seed: int, cases: int = 1_000_000, holdout_cases: int = 10_000) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("invalid_seed")
        if not 1 <= cases <= MAX_SCENARIOS:
            raise ValueError("invalid_case_count")
        if not 1 <= holdout_cases < cases:
            raise ValueError("invalid_holdout_count")
        self.seed = seed
        self.cases = cases
        self.holdout_cases = holdout_cases
        self._engine = AdversarialEngine(seed=seed, max_scenarios=cases)

    @property
    def manifest(self) -> CampaignManifest:
        raw = f"noryx7-eval:{self.seed}:{self.cases}:{self.holdout_cases}".encode()
        campaign_id = hashlib.sha256(raw).hexdigest()[:24]
        return CampaignManifest(campaign_id, self.seed, self.cases, self.holdout_cases, self.cases - self.holdout_cases)

    def scenario(self, index: int, *, difficulty: int = 1) -> AttackScenario:
        """Return one deterministic generated case without executing it."""
        return self._engine.scenario(index, difficulty=difficulty)

    def is_holdout(self, index: int) -> bool:
        if not 0 <= index < self.cases:
            raise IndexError("scenario_index_out_of_range")
        # Deterministic partition independent of execution order.
        digest = hashlib.sha256(f"holdout:{self.seed}:{index}".encode()).digest()
        return int.from_bytes(digest[:8], "big") % self.cases < self.holdout_cases

    def record(self, matrix: EvaluationMatrix, *, dimension: EvaluationDimension, passed: bool, score: float, evidence: str) -> None:
        """Record independently produced evidence; this layer does not infer truth."""
        matrix.record(EvaluationResult(dimension, passed, score, evidence))

    @staticmethod
    def approve(matrix: EvaluationMatrix) -> bool:
        """Fail closed: no evidence or any failed dimension means rejection."""
        return matrix.passed()
