"""Bounded Universal Intelligence Fabric contracts.

The fabric is domain-neutral: specialists produce evidence-bearing proposals;
verification decides whether a proposal is eligible for trusted commitment.
Specialists never receive authorization or state-commit authority here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .contracts import TaskSpec, VerificationResult
from .cognitive_divergence import BranchingCognitionEngine


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    claim: str
    strength: float = 0.0

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.evidence_id, str) and bool(self.evidence_id.strip())
            and isinstance(self.source, str) and bool(self.source.strip())
            and isinstance(self.claim, str) and bool(self.claim.strip())
            and isinstance(self.strength, (int, float)) and 0.0 <= float(self.strength) <= 1.0
        )


@dataclass(frozen=True)
class DomainAssessment:
    domain: str
    conclusion: str
    evidence: tuple[Evidence, ...] = ()
    confidence: float = 0.0
    uncertainty: float = 1.0
    contradictions: tuple[str, ...] = ()
    risk_level: str = "normal"
    strategy: str = "standard"

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.domain, str) and bool(self.domain.strip())
            and isinstance(self.conclusion, str) and bool(self.conclusion.strip())
            and isinstance(self.evidence, tuple)
            and all(isinstance(item, Evidence) and item.is_well_formed() for item in self.evidence)
            and isinstance(self.confidence, (int, float)) and 0.0 <= float(self.confidence) <= 1.0
            and isinstance(self.uncertainty, (int, float)) and 0.0 <= float(self.uncertainty) <= 1.0
            and isinstance(self.contradictions, tuple)
            and all(isinstance(item, str) and bool(item.strip()) for item in self.contradictions)
            and isinstance(self.risk_level, str) and bool(self.risk_level.strip())
            and isinstance(self.strategy, str) and bool(self.strategy.strip())
        )


@dataclass(frozen=True)
class SpecialistRoute:
    domain: str
    strategy: str
    budget: str
    rationale: str

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.domain, str) and bool(self.domain.strip())
            and isinstance(self.strategy, str) and bool(self.strategy.strip())
            and isinstance(self.budget, str) and bool(self.budget.strip())
            and isinstance(self.rationale, str) and bool(self.rationale.strip())
        )


@dataclass(frozen=True)
class FabricResult:
    task_id: str
    assessments: tuple[DomainAssessment, ...]
    evidence_coverage: float
    contradiction: bool
    commit_eligible: bool
    verification: VerificationResult
    metadata: Mapping[str, Any] = field(default_factory=dict)


class UniversalIntelligenceFabric:
    """Coordinate bounded domain assessment and deterministic specialist routing."""

    STRATEGIES = ("pythagorean", "apollonian", "eurelian", "branching_lateral")
    BUDGETS = ("reflex", "standard", "deep", "specialist", "multi_agent", "simulation", "independent_verification", "branching")
    DOMAINS = (
        "software_engineering",
        "architecture_engineering",
        "legal_intelligence",
        "medical_evidence",
        "scientific_research",
        "finance_economics",
        "general_reasoning",
    )
    _DOMAIN_KEYWORDS = {
        "software_engineering": ("code", "coding", "program", "python", "javascript", "bug", "test", "api", "repository", "software"),
        "architecture_engineering": ("architecture", "system design", "distributed", "infrastructure", "hardware", "network", "scalability"),
        "legal_intelligence": ("law", "legal", "contract", "regulation", "compliance", "court", "statute"),
        "medical_evidence": ("medical", "medicine", "clinical", "diagnosis", "symptom", "treatment", "drug"),
        "scientific_research": ("science", "research", "experiment", "hypothesis", "paper", "physics", "chemistry", "biology"),
        "finance_economics": ("finance", "financial", "investment", "economy", "economics", "market", "stock", "budget", "revenue"),
    }

    def __init__(self, *, branching_engine: BranchingCognitionEngine | None = None):
        self.branching_engine = branching_engine or BranchingCognitionEngine()
        if not isinstance(self.branching_engine, BranchingCognitionEngine):
            raise TypeError("invalid_branching_cognition_engine")

    def route(self, task: TaskSpec) -> SpecialistRoute:
        """Select a bounded cognitive route; this changes cognition, never authority."""
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        objective = task.objective.lower()
        task_input = (task.input or "").lower()
        text = f"{task.task_type} {task.objective} {task.input or ''}".lower()
        domain = "general_reasoning"
        best_score = 0
        for candidate, keywords in self._DOMAIN_KEYWORDS.items():
            objective_score = sum(1 for keyword in keywords if keyword in objective)
            input_score = sum(1 for keyword in keywords if keyword in task_input)
            score = objective_score * 3 + input_score
            if score > best_score:
                best_score, domain = score, candidate
        if task.risk_class.lower() in {"high", "critical"}:
            budget = "independent_verification"
            strategy = "eurelian"
        elif domain != "general_reasoning":
            budget = "specialist"
            strategy = ("pythagorean", "apollonian", "eurelian")[best_score % 3]
        elif len(text) > 600:
            budget = "deep"
            strategy = "apollonian"
        else:
            budget = "standard"
            strategy = "standard"
        branching_markers = ("compare", "alternative", "hypothesis", "experiment", "why", "unknown", "multiple", "different")
        if domain in {"scientific_research", "architecture_engineering"} or any(marker in text for marker in branching_markers):
            assessment = self.branching_engine.explore(task, max_branches=5)
            if assessment.verification.valid:
                strategy = "branching_lateral"
                budget = "branching"
        return SpecialistRoute(domain, strategy, budget, f"deterministic objective/context/risk routing; domain_score={best_score}")

    def assess(self, task: TaskSpec, assessments: tuple[DomainAssessment, ...], *, budget: str = "standard") -> FabricResult:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return self._rejected("", "invalid_task")
        if not isinstance(assessments, tuple) or not assessments:
            return self._rejected(task.task_id, "no_domain_assessments")
        if budget not in self.BUDGETS:
            return self._rejected(task.task_id, "invalid_cognitive_budget")
        if any(not isinstance(item, DomainAssessment) or not item.is_well_formed() for item in assessments):
            return self._rejected(task.task_id, "malformed_domain_assessment")
        domains = [item.domain for item in assessments]
        if len(domains) != len(set(domains)):
            return self._rejected(task.task_id, "duplicate_domain_assessment")
        allowed_strategies = set(self.STRATEGIES) | {"standard"}
        strategies = {item.strategy for item in assessments}
        if not strategies.issubset(allowed_strategies):
            return self._rejected(task.task_id, "invalid_cognitive_strategy")
        evidence_items = [item for assessment in assessments for item in assessment.evidence]
        coverage = 0.0 if not evidence_items else sum(float(item.strength) for item in evidence_items) / len(evidence_items)
        contradiction = any(bool(item.contradictions) for item in assessments)
        high_risk = any(item.risk_level.lower() in {"high", "critical"} for item in assessments)
        high_uncertainty = any(float(item.uncertainty) > 0.5 for item in assessments)
        verification = VerificationResult(
            not contradiction and not high_uncertainty,
            "universal_intelligence",
            "fabric_assessment_ok" if not contradiction and not high_uncertainty else "contradiction_or_uncertainty",
            (f"evidence_coverage={coverage:.3f}", f"budget={budget}", f"risk_high={high_risk}"),
        )
        return FabricResult(task.task_id, assessments, coverage, contradiction, bool(verification.valid and not high_risk), verification, {"budget": budget, "domains": tuple(domains)})

    @staticmethod
    def _rejected(task_id: str, reason: str) -> FabricResult:
        verification = VerificationResult(False, "universal_intelligence", reason)
        return FabricResult(task_id, (), 0.0, False, False, verification, {})
