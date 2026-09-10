"""Bounded divergent cognition primitives for NORYX7.

This is an architectural reasoning mode, not a claim to reproduce a clinical
neurotype. It explores multiple independent paths, source types, and patterns
while remaining bounded and non-authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable

from .contracts import TaskSpec, VerificationResult
from .pattern_neural import PatternNeuralNetwork


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
    neural_patterns: tuple[str, ...]
    verification: VerificationResult


class BranchingCognitionEngine:
    """Create bounded alternative lenses using optional authorized evidence."""

    LENSES = ("direct", "analogical", "adversarial", "systems", "cross_domain")
    SOURCE_CLASSES = ("direct_evidence", "historical", "structural", "counterexample", "cross_domain")

    def __init__(self, neural_network: PatternNeuralNetwork | None = None, source_provider: Callable[[TaskSpec], Any] | None = None) -> None:
        self.neural_network = neural_network or PatternNeuralNetwork()
        self.source_provider = source_provider

    def _authorized_sources(self, task: TaskSpec) -> tuple[Any, ...]:
        if self.source_provider is None:
            return ()
        try:
            sources = tuple(self.source_provider(task))
        except Exception:
            return ()
        return tuple(item for item in sources if getattr(item, "access_status", "") in {"authorized", "metadata_only"})

    def explore(self, task: TaskSpec, *, max_branches: int = 5) -> BranchingAssessment:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return BranchingAssessment((), 0, 0, (), VerificationResult(False, "branching_cognition", "invalid_task"))
        if isinstance(max_branches, bool) or not isinstance(max_branches, int) or not 1 <= max_branches <= len(self.LENSES):
            return BranchingAssessment((), 0, 0, (), VerificationResult(False, "branching_cognition", "invalid_branch_budget"))
        text = f"{task.task_type} {task.objective} {task.input or ''}".lower()
        tags = self._patterns(text)
        neural = tuple(item.label for item in self.neural_network.recognize_text(text) if item.score >= 0.55)
        sources = self._authorized_sources(task)
        source_types = tuple(dict.fromkeys(str(getattr(source, "source_type", "direct_evidence")) for source in sources))
        source_disciplines = tuple(dict.fromkeys(str(getattr(source, "discipline", "")) for source in sources if getattr(source, "discipline", "")))
        evidence_context = tuple(source_types[:4])
        branches = []
        for index, lens in enumerate(self.LENSES[:max_branches]):
            fallback = (self.SOURCE_CLASSES[index], self.SOURCE_CLASSES[(index + 1) % len(self.SOURCE_CLASSES)])
            source = evidence_context[:2] if len(evidence_context) >= 2 else fallback
            if len(source) == 1:
                source = (source[0], self.SOURCE_CLASSES[(index + 1) % len(self.SOURCE_CLASSES)])
            digest = sha256(f"{task.task_id}|{lens}|{task.objective}".encode()).hexdigest()[:16]
            evidence_label = ",".join(source_disciplines[:3]) or "no_authorized_source"
            branches.append(CognitiveBranch(
                branch_id=f"{task.task_id}:branch:{digest}",
                lens=lens,
                hypothesis=f"evaluate:{lens}:{task.objective[:240]}|evidence={evidence_label}",
                source_classes=tuple(source),
                pattern_tags=tags + neural,
            ))
        # Fallback source classes describe reasoning lenses only; they are not
        # external evidence. Diversity therefore means distinct authorized
        # evidence classes, not merely the number of source records.
        diversity = len(set(source_types))
        check = VerificationResult(
            bool(branches) and diversity >= 3,
            "branching_cognition",
            "branch_set_ok" if branches and diversity >= 3 else "insufficient_source_diversity",
            (f"branches={len(branches)}", f"source_diversity={diversity}", f"source_records={len(sources)}", f"patterns={len(tags)}", f"neural_patterns={len(neural)}", f"authorized_sources={len(sources)}"),
        )
        return BranchingAssessment(tuple(branches), diversity, len(tags), neural, check)

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
