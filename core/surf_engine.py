"""SURF: evidence-grounded System Understanding & Reverse Engineering Fabric."""
from dataclasses import dataclass
from .surf_contracts import EvidenceRecord, SystemGraph, HypothesisRecord, Experiment, ImprovementCandidate, MAX_RECORDS

@dataclass(frozen=True)
class SURFAssessment:
    graph_valid: bool
    evidence_count: int
    verified_hypotheses: int
    contradictions: int
    unknowns: int
    improvement_ready: bool

class SURFEngine:
    """Evidence-first assessment only; target access and execution stay adapter-owned."""
    def assess(self, graph: SystemGraph, evidence: tuple[EvidenceRecord, ...] = (),
               hypotheses: tuple[HypothesisRecord, ...] = (),
               experiments: tuple[Experiment, ...] = (),
               candidates: tuple[ImprovementCandidate, ...] = ()) -> SURFAssessment:
        invalid = SURFAssessment(False, 0, 0, 0, 0, False)
        if not isinstance(graph, SystemGraph) or not graph.is_well_formed():
            return invalid
        groups = (evidence, hypotheses, experiments, candidates)
        if not all(isinstance(group, tuple) and len(group) <= MAX_RECORDS for group in groups):
            return invalid
        if not all(isinstance(item, EvidenceRecord) and item.is_well_formed() for item in evidence):
            return invalid
        graph_evidence = {item.evidence_id: item for item in graph.evidence}
        if evidence and (len(evidence) != len(graph_evidence)
                         or {item.evidence_id: item for item in evidence} != graph_evidence):
            return invalid
        verified = sum(1 for item in hypotheses if isinstance(item, HypothesisRecord)
                       and _well_formed(item) and item.status == "verified")
        contradictions = sum(1 for item in hypotheses if isinstance(item, HypothesisRecord)
                            and _well_formed(item) and item.status == "contradicted")
        unknowns = sum(1 for node in graph.nodes if node.state == "unknown")
        unknowns += sum(1 for edge in graph.edges if edge.state == "unknown")
        ready = bool(candidates) and all(
            isinstance(item, ImprovementCandidate) and _well_formed(item)
            and item.verified and item.regression_passed for item in candidates
        )
        return SURFAssessment(True, len(graph.evidence), verified, contradictions, unknowns, ready)

    @staticmethod
    def approve_experiment(experiment: Experiment) -> bool:
        return (isinstance(experiment, Experiment) and _well_formed(experiment)
                and experiment.authorized and experiment.sandboxed)


def _well_formed(value: object) -> bool:
    try:
        return bool(value.is_well_formed())  # type: ignore[attr-defined]
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
