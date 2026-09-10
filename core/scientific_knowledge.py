"""Scientific knowledge fabric for lawful, provenance-aware research workflows.

The fabric is deliberately source-neutral: it can ingest metadata, abstracts,
full text, datasets, and experiment results only when the caller is authorized
to access them. It never treats an unverified paper as truth and never grants
execution authority to research content.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    title: str
    discipline: str
    source_type: str
    uri: str
    access_status: str = "authorized"
    license: str = "unknown"
    abstract: str = ""
    content_digest: str = ""

    def is_well_formed(self) -> bool:
        return all(isinstance(value, str) and value.strip() for value in (
            self.source_id, self.title, self.discipline, self.source_type, self.uri,
        )) and self.access_status in {"authorized", "metadata_only", "restricted"}

    @staticmethod
    def digest_content(content: str) -> str:
        if not isinstance(content, str):
            raise TypeError("research_content_must_be_text")
        return sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResearchHypothesis:
    hypothesis_id: str
    statement: str
    source_ids: tuple[str, ...]
    confidence: float
    falsifiers: tuple[str, ...]
    experiment_plan: tuple[str, ...]

    def is_well_formed(self) -> bool:
        return (
            bool(self.hypothesis_id.strip())
            and bool(self.statement.strip())
            and bool(self.source_ids)
            and 0.0 <= self.confidence <= 1.0
            and bool(self.falsifiers)
            and bool(self.experiment_plan)
        )


@dataclass(frozen=True)
class ResearchExperiment:
    experiment_id: str
    hypothesis_id: str
    method: str
    inputs_digest: str
    result_summary: str
    verified: bool


class ScientificKnowledgeFabric:
    """Bounded research memory plus hypothesis/experiment admission."""

    DISCIPLINES = (
        "physics", "mathematics", "computer_science", "biology", "chemistry",
        "medicine", "engineering", "earth_science", "social_science",
        "economics", "history", "linguistics", "materials", "interdisciplinary",
    )

    def __init__(self, *, max_sources: int = 10000, max_hypotheses: int = 1000, max_experiments: int = 1000):
        if min(max_sources, max_hypotheses, max_experiments) < 1:
            raise ValueError("research_limits_must_be_positive")
        self.max_sources = int(max_sources)
        self.max_hypotheses = int(max_hypotheses)
        self.max_experiments = int(max_experiments)
        self._sources: dict[str, ResearchSource] = {}
        self._hypotheses: dict[str, ResearchHypothesis] = {}
        self._experiments: dict[str, ResearchExperiment] = {}

    def add_source(self, source: ResearchSource) -> str:
        if not isinstance(source, ResearchSource) or not source.is_well_formed():
            raise ValueError("invalid_research_source")
        if source.access_status not in {"authorized", "metadata_only"}:
            raise PermissionError("research_source_access_not_authorized")
        if len(self._sources) >= self.max_sources and source.source_id not in self._sources:
            raise RuntimeError("research_source_capacity_exceeded")
        self._sources[source.source_id] = source
        return source.source_id

    def add_sources(self, sources: Iterable[ResearchSource]) -> tuple[str, ...]:
        return tuple(self.add_source(source) for source in sources)

    def sources(self, discipline: str | None = None) -> tuple[ResearchSource, ...]:
        values = tuple(self._sources.values())
        if discipline is None:
            return values
        return tuple(item for item in values if item.discipline == discipline)

    def formulate_hypothesis(self, *, hypothesis_id: str, statement: str, source_ids: Iterable[str], confidence: float, falsifiers: Iterable[str], experiment_plan: Iterable[str]) -> ResearchHypothesis:
        source_ids = tuple(dict.fromkeys(source_ids))
        hypothesis = ResearchHypothesis(hypothesis_id, statement, source_ids, float(confidence), tuple(falsifiers), tuple(experiment_plan))
        if not hypothesis.is_well_formed():
            raise ValueError("invalid_research_hypothesis")
        if any(source_id not in self._sources for source_id in source_ids):
            raise ValueError("hypothesis_source_missing")
        if len(self._hypotheses) >= self.max_hypotheses and hypothesis_id not in self._hypotheses:
            raise RuntimeError("research_hypothesis_capacity_exceeded")
        self._hypotheses[hypothesis_id] = hypothesis
        return hypothesis

    def admit_experiment(self, experiment: ResearchExperiment) -> ResearchExperiment:
        if not isinstance(experiment, ResearchExperiment) or not experiment.experiment_id.strip() or not experiment.hypothesis_id.strip():
            raise ValueError("invalid_research_experiment")
        if experiment.hypothesis_id not in self._hypotheses:
            raise ValueError("experiment_hypothesis_missing")
        if not experiment.verified:
            raise PermissionError("unverified_experiment_result")
        if len(self._experiments) >= self.max_experiments and experiment.experiment_id not in self._experiments:
            raise RuntimeError("research_experiment_capacity_exceeded")
        self._experiments[experiment.experiment_id] = experiment
        return experiment

    def hypothesis(self, hypothesis_id: str) -> ResearchHypothesis | None:
        return self._hypotheses.get(hypothesis_id)

    def experiments(self, hypothesis_id: str | None = None) -> tuple[ResearchExperiment, ...]:
        values = tuple(self._experiments.values())
        if hypothesis_id is None:
            return values
        return tuple(item for item in values if item.hypothesis_id == hypothesis_id)

    def research_context(self, *, disciplines: Iterable[str] = (), limit: int = 12) -> tuple[ResearchSource, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("invalid_research_context_limit")
        selected = tuple(disciplines)
        if selected:
            values = tuple(item for item in self._sources.values() if item.discipline in selected)
        else:
            values = tuple(self._sources.values())
        return values[:limit]
