"""Bounded divergent cognition primitives for NORYX7.

This is an architectural reasoning mode, not a claim to reproduce a clinical
neurotype. It deliberately explores multiple independent paths, source types,
and cross-domain patterns before selecting a bounded execution plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .contracts import TaskSpec, VerificationResult


@dataclass(frozen=True)
class CognitiveBranch:
    branch_id: str
    lens: str
    hypothesis: str
    source_classes: tuple[str, ...]
    pattern_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class BranchingAssessment:
    branches: tuple[CognitiveBranch, ...]
    source_diversity: int
    pattern_count: int
    verification: VerificationResult


class BranchingCognitionEngine:
    """Create bounded alternative lenses without exposing private reasoning traces."""

    LENSES = ("direct", "analogical", "adversarial", "systems", "cross_domain")
    SOURCE_CLASSES = ("direct_evidence", "historical", "structural", "counterexample", "cross_domain")

    def explore(self, task: TaskSpec, *, max_branches: int = 5) -> BranchingAssessment:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return BranchingAssessment((), 0, 0, VerificationResult(False, "branching_cognition", "invalid_task"))
        if isinstance(max_branches, bool) or not isinstance(max_branches, int) or not 1 <= max_branches <= len(self.LENSES):
            return BranchingAssessment((), 0, 0, VerificationResult(False, "branching_cognition", "invalid_branch_budget"))
        text = f"{task.task_type} {task.objective} {task.input or ''}".lower()
        tags = self._patterns(text)
        branches = []
        for index, lens in enumerate(self.LENSES[:max_branches]):
            source = (self.SOURCE_CLASSES[index], self.SOURCE_CLASSES[(index + 1) % len(self.SOURCE_CLASSES)])
            digest = sha256(f"{task.task_id}|{lens}|{task.objective}".encode()).hexdigest()[:16]
            branches.append(CognitiveBranch(
                branch_id=f"{task.task_id}:branch:{digest}",
                lens=lens,
                hypothesis=f"evaluate:{lens}:{task.objective[:240]}",
                source_classes=source,
                pattern_tags=tags,
            ))
        diversity = len({source for branch in branches for source in branch.source_classes})
        check = VerificationResult(
            bool(branches) and diversity >= 3,
            "branching_cognition",
            "branch_set_ok" if branches and diversity >= 3 else "insufficient_source_diversity",
            (f"branches={len(branches)}", f"source_diversity={diversity}", f"patterns={len(tags)}"),
        )
        return BranchingAssessment(tuple(branches), diversity, len(tags), check)

    @staticmethod
    def _patterns(text: str) -> tuple[str, ...]:
        markers = {
            "causal": ("because", "cause", "effect", "why", "impact"),
            "contrast": ("versus", "vs", "compare", "difference", "alternative"),
            "temporal": ("before", "after", "history", "trend", "future"),
            "structural": ("system", "architecture", "network", "dependency", "constraint"),
            "quantitative": ("equation", "calculate", "number", "data", "probability", "navier", "stokes"),
            "anomaly": ("unexpected", "anomaly", "exception", "failure", "edge case"),
        }
        return tuple(name for name, words in markers.items() if any(word in text for word in words))

    def verify(self, assessment: BranchingAssessment) -> VerificationResult:
        if not isinstance(assessment, BranchingAssessment):
            return VerificationResult(False, "branching_cognition", "invalid_assessment")
        ids = [branch.branch_id for branch in assessment.branches]
        if len(ids) != len(set(ids)):
            return VerificationResult(False, "branching_cognition", "duplicate_branch_id")
        if any(branch.lens not in self.LENSES for branch in assessment.branches):
            return VerificationResult(False, "branching_cognition", "invalid_lens")
        if any(not branch.source_classes for branch in assessment.branches):
            return VerificationResult(False, "branching_cognition", "missing_source_classes")
        return assessment.verification
