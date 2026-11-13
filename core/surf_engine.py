"""SURF: evidence-grounded System Understanding & Reverse Engineering Fabric."""
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
from typing import Callable, Mapping

from core.identity import AgentAttestation, AgentIdentityAuthority, IdentityRegistry

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
    verification_trust_level: str = "callback_claims_only"


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


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("surf_receipt_mapping_keys_must_be_strings")
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError("surf_receipt_payload_not_canonical_json")


def surf_receipt_statement(receipt_type: str, subject, context) -> bytes:
    """Canonical statement a trusted verifier must sign for one SURF decision."""
    if not isinstance(receipt_type, str) or not receipt_type.strip() or len(receipt_type) > 128:
        raise ValueError("invalid_surf_receipt_type")
    subject_bytes = json.dumps(
        _jsonable(subject), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    context_bytes = json.dumps(
        _jsonable(context), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    statement = {
        "domain": "NORYX7_SURF_TRUSTED_RECEIPT_V1",
        "receipt_type": receipt_type,
        "subject_digest": hashlib.sha256(subject_bytes).hexdigest(),
        "context_digest": hashlib.sha256(context_bytes).hexdigest(),
    }
    return json.dumps(
        statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


class SURFEngine:
    """Evidence-first assessment with optional identity-bound signed verifier receipts.

    Legacy boolean callbacks remain available for compatibility but are labelled
    callback_claims_only. When a trusted receipt provider and IdentityRegistry are
    configured, callbacks are not used for trust decisions: every counted result
    must carry an Ed25519 AgentAttestation from a registered verifier identity.
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
        trusted_receipt_provider: Callable[[str, bytes], AgentAttestation | None] | None = None,
        trusted_identity_registry: IdentityRegistry | None = None,
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
        if trusted_receipt_provider is not None and not callable(trusted_receipt_provider):
            raise TypeError("trusted_receipt_provider_must_be_callable")
        if (trusted_receipt_provider is None) != (trusted_identity_registry is None):
            raise ValueError("trusted_receipt_provider_and_identity_registry_required_together")
        if trusted_identity_registry is not None and not isinstance(trusted_identity_registry, IdentityRegistry):
            raise TypeError("trusted_identity_registry_must_be_IdentityRegistry")
        self._evidence_verifier = evidence_verifier
        self._hypothesis_verifier = hypothesis_verifier
        self._authorization_verifier = authorization_verifier
        self._sandbox_verifier = sandbox_verifier
        self._candidate_verifier = candidate_verifier
        self._regression_verifier = regression_verifier
        self._trusted_receipt_provider = trusted_receipt_provider
        self._trusted_identity_registry = trusted_identity_registry

    @property
    def verification_trust_level(self) -> str:
        return "trusted_identity_signed_receipts" if self._trusted_receipt_provider is not None else "callback_claims_only"

    def _trusted_verified(self, receipt_type: str, subject, context) -> bool:
        if self._trusted_receipt_provider is None or self._trusted_identity_registry is None:
            return False
        try:
            statement = surf_receipt_statement(receipt_type, subject, context)
            receipt = self._trusted_receipt_provider(receipt_type, statement)
        except Exception:
            return False
        return (
            isinstance(receipt, AgentAttestation)
            and receipt.statement == statement
            and AgentIdentityAuthority.verify(receipt, self._trusted_identity_registry)
        )

    def assess(
        self,
        graph: SystemGraph,
        evidence: tuple[EvidenceRecord, ...] = (),
        hypotheses: tuple[HypothesisRecord, ...] = (),
        experiments: tuple[Experiment, ...] = (),
        candidates: tuple[ImprovementCandidate, ...] = (),
    ) -> SURFAssessment:
        invalid = SURFAssessment(False, 0, 0, 0, 0, False, 0, self.verification_trust_level)
        if not isinstance(graph, SystemGraph) or not graph.is_well_formed():
            return invalid
        groups = (evidence, hypotheses, experiments, candidates)
        if not all(isinstance(group, tuple) and len(group) <= MAX_RECORDS for group in groups):
            return invalid
        if not all(isinstance(item, EvidenceRecord) and _well_formed(item) for item in evidence):
            return invalid
        if not all(isinstance(item, Experiment) and _well_formed(item) for item in experiments):
            return invalid
        if len({item.experiment_id for item in experiments}) != len(experiments):
            return invalid
        graph_evidence = {item.evidence_id: item for item in graph.evidence}
        if evidence and (
            len(evidence) != len(graph_evidence)
            or {item.evidence_id: item for item in evidence} != graph_evidence
        ):
            return invalid
        valid_hypotheses = tuple(
            item for item in hypotheses
            if isinstance(item, HypothesisRecord) and _well_formed(item)
        )
        valid_candidates = tuple(
            item for item in candidates
            if isinstance(item, ImprovementCandidate) and _well_formed(item)
        )
        if len({item.hypothesis_id for item in valid_hypotheses}) != len(valid_hypotheses):
            return invalid
        if len({item.candidate_id for item in valid_candidates}) != len(valid_candidates):
            return invalid

        verified_evidence_ids = set()
        for item in graph.evidence:
            if self._trusted_receipt_provider is not None:
                verified = self._trusted_verified("evidence", item, graph)
            else:
                verified = _verified(self._evidence_verifier, item, graph)
            if verified:
                verified_evidence_ids.add(item.evidence_id)

        verified_hypotheses = 0
        contradictions = 0
        for item in valid_hypotheses:
            if not set(item.evidence_ids) <= verified_evidence_ids:
                continue
            context = {
                "graph_id": graph.graph_id,
                "verified_evidence_ids": sorted(verified_evidence_ids),
            }
            if self._trusted_receipt_provider is not None:
                verified = self._trusted_verified("hypothesis", item, context)
            else:
                verified = _verified(
                    self._hypothesis_verifier, item, graph,
                    frozenset(verified_evidence_ids),
                )
            if verified:
                if item.status == "verified":
                    verified_hypotheses += 1
                elif item.status == "contradicted":
                    contradictions += 1

        unknowns = sum(1 for node in graph.nodes if node.state == "unknown")
        unknowns += sum(1 for edge in graph.edges if edge.state == "unknown")

        improvement_ready = bool(valid_candidates) and (
            self._trusted_receipt_provider is not None
            or (self._candidate_verifier is not None and self._regression_verifier is not None)
        )
        if improvement_ready:
            for candidate in valid_candidates:
                if not candidate.verification_receipt or not candidate.regression_receipt:
                    improvement_ready = False
                    break
                context = {"graph_id": graph.graph_id, "verified_evidence_ids": sorted(verified_evidence_ids)}
                if self._trusted_receipt_provider is not None:
                    candidate_ok = self._trusted_verified(
                        "candidate", {"candidate": candidate, "receipt": candidate.verification_receipt}, context
                    )
                    regression_ok = self._trusted_verified(
                        "regression", {"candidate_id": candidate.candidate_id, "receipt": candidate.regression_receipt}, context
                    )
                else:
                    candidate_ok = _verified(
                        self._candidate_verifier, candidate, graph,
                        frozenset(verified_evidence_ids),
                    )
                    regression_ok = _verified(self._regression_verifier, candidate, graph)
                if not candidate_ok or not regression_ok:
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
            self.verification_trust_level,
        )

    def approve_experiment(self, experiment: Experiment) -> bool:
        if not isinstance(experiment, Experiment) or not _well_formed(experiment):
            return False
        if not experiment.authorized or not experiment.sandboxed:
            return False
        if not experiment.authorization_receipt or not experiment.sandbox_receipt:
            return False
        if self._trusted_receipt_provider is not None:
            return (
                self._trusted_verified(
                    "authorization",
                    {"receipt": experiment.authorization_receipt},
                    experiment,
                )
                and self._trusted_verified(
                    "sandbox",
                    {"receipt": experiment.sandbox_receipt},
                    experiment,
                )
            )
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
