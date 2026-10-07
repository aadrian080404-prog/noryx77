"""SURF: evidence-grounded System Understanding & Reverse Engineering Fabric."""
from dataclasses import dataclass
from .surf_contracts import EvidenceRecord, SystemGraph, HypothesisRecord, Experiment, ImprovementCandidate

@dataclass(frozen=True)
class SURFAssessment:
    graph_valid: bool
    evidence_count: int
    verified_hypotheses: int
    contradictions: int
    unknowns: int
    improvement_ready: bool

class SURFEngine:
    """Coordinates safe, evidence-first system understanding.

    This layer deliberately does not acquire arbitrary external access or execute targets.
    Adapters must enforce scope, authorization, sandboxing and resource limits before
    submitting observations or experiments.
    """
    def assess(self, graph: SystemGraph, evidence: tuple[EvidenceRecord,...],
               hypotheses: tuple[HypothesisRecord,...] = (),
               experiments: tuple[Experiment,...] = (),
               candidates: tuple[ImprovementCandidate,...] = ()) -> SURFAssessment:
        if not isinstance(graph,SystemGraph) or not graph.is_well_formed():
            return SURFAssessment(False,0,0,0,0,False)
        valid_evidence = tuple(e for e in evidence if isinstance(e,EvidenceRecord) and e.is_well_formed())
        verified = sum(h.status == "verified" for h in hypotheses if isinstance(h,HypothesisRecord))
        contradictions = sum(h.status == "contradicted" for h in hypotheses if isinstance(h,HypothesisRecord))
        unknowns = sum(1 for n in graph.nodes if n.state == "unknown") + sum(1 for e in graph.edges if e.state == "unknown")
        ready = bool(candidates) and all(isinstance(c,ImprovementCandidate) and c.verified and c.regression_passed for c in candidates)
        return SURFAssessment(True,len(valid_evidence),verified,contradictions,unknowns,ready)

    @staticmethod
    def approve_experiment(experiment: Experiment) -> bool:
        return isinstance(experiment,Experiment) and experiment.is_well_formed() and experiment.authorized and experiment.sandboxed
