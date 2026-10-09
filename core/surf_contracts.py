"""SURF evidence-grounded system understanding contracts."""
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

VALID_STATES = frozenset({"observed","inferred","hypothesized","verified","contradicted","unknown"})
MAX_RECORDS = 4096

def _text(v):
    return isinstance(v, str) and bool(v.strip())

def _refs(v):
    return isinstance(v, tuple) and len(v) <= MAX_RECORDS and all(_text(x) for x in v) and len(set(v)) == len(v)

def _confidence(v):
    return isinstance(v, (int,float)) and not isinstance(v,bool) and isfinite(v) and 0.0 <= v <= 1.0

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
        return (_text(self.evidence_id) and _text(self.kind) and _text(self.source) and _text(self.summary)
                and _confidence(self.confidence) and self.state in VALID_STATES
                and isinstance(self.execution_id,str) and len(self.execution_id) <= 256
                and isinstance(self.provenance,str) and len(self.provenance) <= 2048)

@dataclass(frozen=True)
class SystemNode:
    node_id: str
    node_type: str
    label: str
    evidence_ids: tuple[str,...] = ()
    state: str = "observed"
    def is_well_formed(self) -> bool:
        return _text(self.node_id) and _text(self.node_type) and _text(self.label) and _refs(self.evidence_ids) and self.state in VALID_STATES

@dataclass(frozen=True)
class SystemEdge:
    source_id: str
    target_id: str
    relation: str
    evidence_ids: tuple[str,...] = ()
    confidence: float = 0.0
    state: str = "inferred"
    def is_well_formed(self) -> bool:
        return (_text(self.source_id) and _text(self.target_id) and _text(self.relation) and _refs(self.evidence_ids)
                and _confidence(self.confidence) and self.state in VALID_STATES)

@dataclass(frozen=True)
class SystemGraph:
    graph_id: str
    nodes: tuple[SystemNode,...] = ()
    edges: tuple[SystemEdge,...] = ()
    evidence: tuple[EvidenceRecord,...] = ()
    def is_well_formed(self) -> bool:
        try:
            if not _text(self.graph_id): return False
            groups = (self.nodes,self.edges,self.evidence)
            if not all(isinstance(g,tuple) and len(g) <= MAX_RECORDS for g in groups): return False
            if not all(isinstance(e,EvidenceRecord) and e.is_well_formed() for e in self.evidence): return False
            if len({e.evidence_id for e in self.evidence}) != len(self.evidence): return False
            if not all(isinstance(n,SystemNode) and n.is_well_formed() for n in self.nodes): return False
            if not all(isinstance(e,SystemEdge) and e.is_well_formed() for e in self.edges): return False
            nids = {n.node_id for n in self.nodes}; eids = {e.evidence_id for e in self.evidence}
            if len(nids) != len(self.nodes) or len({(e.source_id,e.target_id,e.relation) for e in self.edges}) != len(self.edges): return False
            return all(set(n.evidence_ids) <= eids for n in self.nodes) and all(e.source_id in nids and e.target_id in nids and set(e.evidence_ids) <= eids for e in self.edges)
        except (AttributeError,TypeError,ValueError,OverflowError):
            return False

@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    evidence_ids: tuple[str,...] = ()
    status: str = "hypothesized"
    alternatives: tuple[str,...] = ()
    def is_well_formed(self) -> bool:
        return (_text(self.hypothesis_id) and _text(self.statement) and _refs(self.evidence_ids)
                and self.status in VALID_STATES and isinstance(self.alternatives,tuple)
                and len(self.alternatives) <= MAX_RECORDS and all(_text(x) for x in self.alternatives))

@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    hypothesis_id: str
    objective: str
    variables: Mapping[str,Any] = field(default_factory=dict)
    authorized: bool = False
    sandboxed: bool = True
    def is_well_formed(self) -> bool:
        return (_text(self.experiment_id) and _text(self.hypothesis_id) and _text(self.objective)
                and isinstance(self.variables,Mapping) and len(self.variables) <= 256
                and all(_text(k) for k in self.variables) and isinstance(self.authorized,bool) and isinstance(self.sandboxed,bool))

@dataclass(frozen=True)
class ImprovementCandidate:
    candidate_id: str
    rationale: str
    requirements: tuple[str,...] = ()
    verified: bool = False
    regression_passed: bool = False
    def is_well_formed(self) -> bool:
        return (_text(self.candidate_id) and _text(self.rationale) and isinstance(self.requirements,tuple)
                and len(self.requirements) <= MAX_RECORDS and all(_text(x) for x in self.requirements)
                and isinstance(self.verified,bool) and isinstance(self.regression_passed,bool))
