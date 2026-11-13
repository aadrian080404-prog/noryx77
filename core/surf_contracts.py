"""SURF evidence-grounded system understanding contracts."""
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

VALID_STATES = frozenset({"observed", "inferred", "hypothesized", "verified", "contradicted", "unknown"})
MAX_RECORDS = 4096
MAX_RECEIPT_LENGTH = 2048


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _refs(value):
    return isinstance(value, tuple) and len(value) <= MAX_RECORDS and all(_text(item) for item in value) and len(set(value)) == len(value)


def _confidence(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return isfinite(value) and 0.0 <= value <= 1.0
    except (OverflowError, TypeError, ValueError):
        return False


def _receipt(value):
    return isinstance(value, str) and len(value) <= MAX_RECEIPT_LENGTH


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    kind: str
    source: str
    summary: str
    confidence: float = 0.0
    state: str = "observed"
    execution_id: str = ""
    provenance: str = ""

    def is_well_formed(self) -> bool:
        return (
            _text(self.evidence_id) and _text(self.kind) and _text(self.source) and _text(self.summary)
            and _confidence(self.confidence) and isinstance(self.state, str) and self.state in VALID_STATES
            and isinstance(self.execution_id, str) and len(self.execution_id) <= 256
            and isinstance(self.provenance, str) and len(self.provenance) <= MAX_RECEIPT_LENGTH
        )


@dataclass(frozen=True)
class SystemNode:
    node_id: str
    node_type: str
    label: str
    evidence_ids: tuple[str, ...] = ()
    state: str = "observed"

    def is_well_formed(self) -> bool:
        return (
            _text(self.node_id) and _text(self.node_type) and _text(self.label) and _refs(self.evidence_ids)
            and isinstance(self.state, str) and self.state in VALID_STATES
        )


@dataclass(frozen=True)
class SystemEdge:
    source_id: str
    target_id: str
    relation: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    state: str = "inferred"

    def is_well_formed(self) -> bool:
        return (
            _text(self.source_id) and _text(self.target_id) and _text(self.relation) and _refs(self.evidence_ids)
            and _confidence(self.confidence) and isinstance(self.state, str) and self.state in VALID_STATES
        )


@dataclass(frozen=True)
class SystemGraph:
    graph_id: str
    nodes: tuple[SystemNode, ...] = ()
    edges: tuple[SystemEdge, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()

    def is_well_formed(self) -> bool:
        try:
            if not _text(self.graph_id):
                return False
            groups = (self.nodes, self.edges, self.evidence)
            if not all(isinstance(group, tuple) and len(group) <= MAX_RECORDS for group in groups):
                return False
            if not all(isinstance(item, EvidenceRecord) and item.is_well_formed() for item in self.evidence):
                return False
            if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
                return False
            if not all(isinstance(item, SystemNode) and item.is_well_formed() for item in self.nodes):
                return False
            if not all(isinstance(item, SystemEdge) and item.is_well_formed() for item in self.edges):
                return False
            node_ids = {item.node_id for item in self.nodes}
            evidence_ids = {item.evidence_id for item in self.evidence}
            if len(node_ids) != len(self.nodes):
                return False
            if len({(item.source_id, item.target_id, item.relation) for item in self.edges}) != len(self.edges):
                return False
            return (
                all(set(item.evidence_ids) <= evidence_ids for item in self.nodes)
                and all(
                    item.source_id in node_ids and item.target_id in node_ids
                    and set(item.evidence_ids) <= evidence_ids
                    for item in self.edges
                )
            )
        except (AttributeError, TypeError, ValueError, OverflowError):
            return False


@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    evidence_ids: tuple[str, ...] = ()
    status: str = "hypothesized"
    alternatives: tuple[str, ...] = ()

    def is_well_formed(self) -> bool:
        return (
            _text(self.hypothesis_id) and _text(self.statement) and _refs(self.evidence_ids)
            and isinstance(self.status, str) and self.status in VALID_STATES
            and isinstance(self.alternatives, tuple) and len(self.alternatives) <= MAX_RECORDS
            and all(_text(item) for item in self.alternatives)
        )


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    hypothesis_id: str
    objective: str
    variables: Mapping[str, Any] = field(default_factory=dict)
    authorized: bool = False
    sandboxed: bool = True
    authorization_receipt: str = ""
    sandbox_receipt: str = ""

    def is_well_formed(self) -> bool:
        return (
            _text(self.experiment_id) and _text(self.hypothesis_id) and _text(self.objective)
            and isinstance(self.variables, Mapping) and len(self.variables) <= 256
            and all(_text(key) for key in self.variables)
            and isinstance(self.authorized, bool) and isinstance(self.sandboxed, bool)
            and _receipt(self.authorization_receipt) and _receipt(self.sandbox_receipt)
        )


@dataclass(frozen=True)
class ImprovementCandidate:
    candidate_id: str
    rationale: str
    requirements: tuple[str, ...] = ()
    verified: bool = False
    regression_passed: bool = False
    verification_receipt: str = ""
    regression_receipt: str = ""

    def is_well_formed(self) -> bool:
        return (
            _text(self.candidate_id) and _text(self.rationale)
            and isinstance(self.requirements, tuple) and len(self.requirements) <= MAX_RECORDS
            and all(_text(item) for item in self.requirements)
            and isinstance(self.verified, bool) and isinstance(self.regression_passed, bool)
            and _receipt(self.verification_receipt) and _receipt(self.regression_receipt)
        )
