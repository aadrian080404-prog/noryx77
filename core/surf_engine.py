"""SURF: evidence-grounded System Understanding & Reverse Engineering Fabric."""
from dataclasses import dataclass
from typing import Callable

from .surf_contracts import (
    EvidenceRecord,
    SystemGraph,
    HypothesisRecord,
    Experiment,
    ImprovementCandidate,
    MAX_RECORDS,
)


@dataclass(frozen=True)
class SURFAssessment:
    graph_valid: bool
    evidence_count: int
    verified_hypotheses: int
    contradictions: int
    unknowns: int
    improvement_ready: bool
    verified_evidence_count: int = 0


def _well_formed(value: object) -> bool:
    try:
        return value.is_well_formed() is True  # type: ignore[attr-defined]
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


def _verified(callback, *args) -> bool:
    if not callable(callback):
        return False
    try:
        return callback(*args) is True
    except Exception:
        return False


class SURFEngine:
    """Evidence-first assessment only; target access and execution stay adapter-owned.

    Status flags and receipt identifiers are claims/references, never proof by
    themselves. A host must inject independent verifiers backed by trusted
    identities, signed attestations and a real sandbox before SURF can count
    evidence, verify hypotheses, approve experiments or mark improvements ready.
    """

    def __init__(
        self,
        *,
        evidence_verifier: Callable | None = None,
        hypothesis_verifier: Callable | None = None,
        authorization_verifier: Callable | None = None,
        sandbox_verifier: Callable | None = None,
        candidate_verifier: Callable | None = None,
        regression_verifier: Callable | None = None,
    ) -> None:
        verifiers = (
            evidence_verifier,
            hypothesis_verifier,
            authorization_verifier,
            sandbox_verifier,
            candidate_verifier,
            regression_verifier,
        )
        if any(item is not None and not callable(item) for item in verifiers):
            raise TypeError("SURF verifiers must be callable")
        self._evidence_verifier = evidence_verifier
        self._hypothesis_verifier = hypothesis_verifier
        self._authorization_verifier = authorization_verifier
        self._sandbox_verifier = sandbox_verifier
        self._candidate_verifier = candidate_verifier
        self._regression_verifier = regression_verifier

    def assess(
        self,
        graph: SystemGraph,
        evidence: tuple[EvidenceRecord, ...] = (),
        hypotheses: tuple[HypothesisRecord, ...] = (),
        experiments: tuple[Experiment, ...] = (),
        candidates: tuple[ImprovementCandidate, ...] = (),
    ) -> SURFAssessment:
        invalid = SURFAssessment(False, 0, 0, 0, 0, False, 0)
        if not isinstance(graph, SystemGraph) or not graph.is_well_formed():
            return invalid
        groups = (evidence, hypotheses, experiments, candidates)
        if not all(isinstance(group, tuple) and len(group) <= MAX_RECORDS for group in groups):
            return invalid
        if not all(isinstance(item, EvidenceRecord) and _well_formed(item) for item in evidence):
            return invalid
        graph_evidence = {item.evidence_id: item for item in graph.evidence}
        if evidence and (
            len(evidence) != len(graph_evidence)
            or {item.evidence_id: item for item in evidence} != graph_evidence
        ):
            return invalid
        # Malformed claims are ignored, never counted as evidence or trust.
        valid_hypotheses = tuple(
            item for item in hypotheses
            if isinstance(item, HypothesisRecord) and _well_formed(item)
        )
        valid_candidates = tuple(
            item for item in candidates
            if isinstance(item, ImprovementCandidate) and _well_formed(item)
        )

        verified_evidence_ids = set()
        if self._evidence_verifier is not None:
            for item in graph.evidence:
                if _verified(self._evidence_verifier, item, graph):
                    verified_evidence_ids.add(item.evidence_id)

        verified_hypotheses = 0
        contradictions = 0
        if self._hypothesis_verifier is not None:
            for item in valid_hypotheses:
                if not set(item.evidence_ids) <= verified_evidence_ids:
                    continue
                if _verified(
                    self._hypothesis_verifier,
                    item,
                    graph,
                    frozenset(verified_evidence_ids),
                ):
                    if item.status == "verified":
                        verified_hypotheses += 1
                    elif item.status == "contradicted":
                        contradictions += 1

        unknowns = sum(1 for node in graph.nodes if node.state == "unknown")
        unknowns += sum(1 for edge in graph.edges if edge.state == "unknown")

        improvement_ready = bool(valid_candidates) and self._candidate_verifier is not None and self._regression_verifier is not None
        if improvement_ready:
            for candidate in valid_candidates:
                if not candidate.verification_receipt or not candidate.regression_receipt:
                    improvement_ready = False
                    break
                if not _verified(
                    self._candidate_verifier,
                    candidate,
                    graph,
                    frozenset(verified_evidence_ids),
                ):
                    improvement_ready = False
                    break
                if not _verified(self._regression_verifier, candidate, graph):
                    improvement_ready = False
                    break

        return SURFAssessment(
            True,
            len(graph.evidence),
            verified_hypotheses,
            contradictions,
            unknowns,
            improvement_ready,
            len(verified_evidence_ids),
        )

    def approve_experiment(self, experiment: Experiment) -> bool:
        if not isinstance(experiment, Experiment) or not _well_formed(experiment):
            return False
        if not experiment.authorized or not experiment.sandboxed:
            return False
        if not experiment.authorization_receipt or not experiment.sandbox_receipt:
            return False
        return (
            _verified(
                self._authorization_verifier,
                experiment.authorization_receipt,
                experiment,
            )
            and _verified(
                self._sandbox_verifier,
                experiment.sandbox_receipt,
                experiment,
            )
        )
