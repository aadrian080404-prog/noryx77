"""SURF contracts: evidence-grounded system understanding primitives."""
from dataclasses import dataclass, field
from typing import Any, Mapping

VALID_STATES = frozenset({"observed","inferred","hypothesized","verified","contradicted","unknown"})

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
        return (bool(self.evidence_id.strip()) and bool(self.kind.strip()) and bool(self.source.strip())
                and bool(self.summary.strip()) and self.state in VALID_STATES
                and isinstance(self.confidence,(int,float)) and 0.0 <= float(self.confidence) <= 1.0
                and isinstance(self.execution_id,str) and len(self.execution_id.encode()) <= 256)

@dataclass(frozen=True)
class SystemNode:
    node_id: str
    node_type: str
    label: str
    evidence_ids: tuple[str,...] = ()
    state: str = "observed"
    def is_well_formed(self) -> bool:
        return bool(self.node_id.strip()) and bool(self.node_type.strip()) and bool(self.label.strip()) and self.state in VALID_STATES and len(set(self.evidence_ids)) == len(self.evidence_ids)

@dataclass(frozen=True)
class SystemEdge:
    source_id: str
    target_id: str
    relation: str
    evidence_ids: tuple[str,...] = ()
    confidence: float = 0.0
    state: str = "inferred"
    def is_well_formed(self) -> bool:
        return (bool(self.source_id.strip()) and bool(self.target_id.strip()) and bool(self.relation.strip())
                and self.state in VALID_STATES and len(set(self.evidence_ids)) == len(self.evidence_ids)
                and isinstance(self.confidence,(int,float)) and 0.0 <= float(self.confidence) <= 1.0)

@dataclass(frozen=True)
class SystemGraph:
    graph_id: str
    nodes: tuple[SystemNode,...] = ()
    edges: tuple[SystemEdge,...] = ()
    evidence: tuple[EvidenceRecord,...] = ()
    def is_well_formed(self) -> bool:
        ids = {e.evidence_id for e in self.evidence}
        nids = {n.node_id for n in self.nodes}
        return (bool(self.graph_id.strip()) and len(nids)==len(self.nodes)
                and len({(e.source_id,e.target_id,e.relation) for e in self.edges})==len(self.edges)
                and all(n.is_well_formed() and set(n.evidence_ids) <= ids for n in self.nodes)
                and all(e.is_well_formed() and e.source_id in nids and e.target_id in nids and set(e.evidence_ids) <= ids for e in self.edges))

@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    evidence_ids: tuple[str,...] = ()
    status: str = "hypothesized"
    alternatives: tuple[str,...] = ()
    def is_well_formed(self) -> bool:
        return bool(self.hypothesis_id.strip()) and bool(self.statement.strip()) and self.status in VALID_STATES and len(set(self.evidence_ids)) == len(self.evidence_ids)

@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    hypothesis_id: str
    objective: str
    variables: Mapping[str, Any] = field(default_factory=dict)
    authorized: bool = False
    sandboxed: bool = True
    def is_well_formed(self) -> bool:
        return bool(self.experiment_id.strip()) and bool(self.hypothesis_id.strip()) and bool(self.objective.strip()) and isinstance(self.variables,Mapping) and isinstance(self.authorized,bool) and isinstance(self.sandboxed,bool)

@dataclass(frozen=True)
class ImprovementCandidate:
    candidate_id: str
    rationale: str
    requirements: tuple[str,...] = ()
    verified: bool = False
    regression_passed: bool = False
    def is_well_formed(self) -> bool:
        return bool(self.candidate_id.strip()) and bool(self.rationale.strip()) and all(isinstance(x,str) and x.strip() for x in self.requirements) and isinstance(self.verified,bool) and isinstance(self.regression_passed,bool)
