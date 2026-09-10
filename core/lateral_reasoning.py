"""Bounded lateral/branched reasoning contracts for NORYX7.

This is a cognitive strategy layer, not a claim about human neurodivergence.
It deliberately avoids single-chain A->B reasoning by generating independent
branches, collecting evidence from distinct sources, detecting cross-branch
patterns, and requiring convergence checks before admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .contracts import TaskSpec, VerificationResult


@dataclass(frozen=True)
class ReasoningSource:
    source_id: str
    perspective: str
    claim: str
    strength: float = 0.0

    def is_well_formed(self) -> bool:
        return (
            all(isinstance(v, str) and bool(v.strip()) for v in (self.source_id, self.perspective, self.claim))
            and isinstance(self.strength, (int, float))
            and 0.0 <= float(self.strength) <= 1.0
        )


@dataclass(frozen=True)
class ReasoningBranch:
    branch_id: str
    hypothesis: str
    sources: tuple[ReasoningSource, ...] = ()
    patterns: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.branch_id, str) and bool(self.branch_id.strip())
            and isinstance(self.hypothesis, str) and bool(self.hypothesis.strip())
            and isinstance(self.sources, tuple)
            and all(item.is_well_formed() for item in self.sources)
            and isinstance(self.patterns, tuple)
            and all(isinstance(item, str) and bool(item.strip()) for item in self.patterns)
            and isinstance(self.alternatives, tuple)
            and all(isinstance(item, str) and bool(item.strip()) for item in self.alternatives)
        )


@dataclass(frozen=True)
class LateralReasoningResult:
    task_id: str
    branches: tuple[ReasoningBranch, ...]
    cross_patterns: tuple[str, ...]
    convergence_score: float
    verification: VerificationResult


class LateralReasoningEngine:
    """Generate and verify bounded divergent reasoning rather than one linear chain."""

    MIN_BRANCHES = 3
    MAX_BRANCHES = 8

    def branch_plan(self, task: TaskSpec) -> tuple[str, ...]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        # Independent perspectives force search-space diversity without asking
        # the underlying model to expose private chain-of-thought.
        perspectives = (
            "direct",
            "contrarian",
            "analogical",
            "systems",
            "edge_case",
            "cross_domain",
            "failure_mode",
            "minimal_explanation",
        )
        count = min(self.MAX_BRANCHES, max(self.MIN_BRANCHES, 3 + len(task.objective) // 240))
        return tuple(perspectives[:count])

    def verify(self, task: TaskSpec, branches: Iterable[ReasoningBranch]) -> LateralReasoningResult:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return LateralReasoningResult("", (), (), 0.0, VerificationResult(False, "lateral_reasoning", "invalid_task"))
        branches = tuple(branches)
        if len(branches) < self.MIN_BRANCHES or len(branches) > self.MAX_BRANCHES:
            return LateralReasoningResult(task.task_id, branches, (), 0.0, VerificationResult(False, "lateral_reasoning", "branch_count_out_of_bounds"))
        if any(not item.is_well_formed() for item in branches):
            return LateralReasoningResult(task.task_id, branches, (), 0.0, VerificationResult(False, "lateral_reasoning", "malformed_branch"))
        if len({item.branch_id for item in branches}) != len(branches):
            return LateralReasoningResult(task.task_id, branches, (), 0.0, VerificationResult(False, "lateral_reasoning", "duplicate_branch"))
        source_ids = {source.source_id for branch in branches for source in branch.sources}
        perspectives = {source.perspective for branch in branches for source in branch.sources}
        pattern_counts: dict[str, int] = {}
        for branch in branches:
            for pattern in branch.patterns:
                key = " ".join(pattern.lower().split())
                pattern_counts[key] = pattern_counts.get(key, 0) + 1
        cross_patterns = tuple(sorted(pattern for pattern, count in pattern_counts.items() if count >= 2))
        diversity = min(1.0, len(perspectives) / len(branches))
        evidence = min(1.0, len(source_ids) / max(1, len(branches) * 2))
        convergence = min(1.0, 0.5 * diversity + 0.3 * evidence + 0.2 * min(1.0, len(cross_patterns) / max(1, len(branches))))
        valid = diversity >= 0.66 and evidence >= 0.5 and bool(cross_patterns)
        return LateralReasoningResult(
            task.task_id,
            branches,
            cross_patterns,
            convergence,
            VerificationResult(valid, "lateral_reasoning", "branched_pattern_consensus" if valid else "insufficient_divergence_or_pattern_overlap", (f"branches={len(branches)}", f"sources={len(source_ids)}", f"cross_patterns={len(cross_patterns)}", f"convergence={convergence:.3f}")),
        )

    @staticmethod
    def pattern_fingerprint(patterns: Iterable[str]) -> str:
        canonical = "|".join(sorted(" ".join(item.lower().split()) for item in patterns if item.strip()))
        return sha256(canonical.encode("utf-8")).hexdigest()
