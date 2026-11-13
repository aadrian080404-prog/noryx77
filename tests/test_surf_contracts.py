from core.surf_contracts import (
    EvidenceRecord, SystemNode, SystemEdge, SystemGraph, Experiment,
    HypothesisRecord, ImprovementCandidate,
)
from core.surf_engine import SURFEngine


def _graph(evidence=(), node_state="observed"):
    nodes = (SystemNode("n1", "component", "A", tuple(e.evidence_id for e in evidence), node_state),)
    return SystemGraph("g1", nodes, (), tuple(evidence))


def test_surf_graph_is_evidence_grounded():
    ev = EvidenceRecord("e1", "static", "fixture", "component observed", 0.9)
    assert _graph((ev,)).is_well_formed()


def test_graph_rejects_missing_evidence():
    node = SystemNode("n1", "component", "A", ("missing",))
    assert not SystemGraph("g1", (node,), (), ()).is_well_formed()


def test_graph_rejects_malformed_or_duplicate_evidence():
    malformed = EvidenceRecord("e1", "static", "fixture", "observed", state="invalid")
    assert not SystemGraph("g1", (), (), (malformed,)).is_well_formed()
    ev = EvidenceRecord("e1", "static", "fixture", "observed")
    assert not SystemGraph("g1", (), (), (ev, ev)).is_well_formed()


def test_contracts_fail_closed_on_unhashable_states():
    ev = EvidenceRecord("e1", "static", "fixture", "observed", state=[])
    node = SystemNode("n1", "component", "A", (), [])
    edge = SystemEdge("n1", "n2", "links", (), 0.5, [])
    hypothesis = HypothesisRecord("h1", "statement", (), [])
    assert not ev.is_well_formed()
    assert not node.is_well_formed()
    assert not edge.is_well_formed()
    assert not hypothesis.is_well_formed()
    assert not SystemGraph("g1", (), (), (ev,)).is_well_formed()


def test_experiment_requires_external_authorization_and_sandbox_receipts():
    claimed_only = Experiment("x", "h", "observe", {}, True, True)
    assert not SURFEngine().approve_experiment(claimed_only)

    engine = SURFEngine(
        authorization_verifier=lambda receipt, experiment: receipt == "auth-receipt",
        sandbox_verifier=lambda receipt, experiment: receipt == "sandbox-attestation",
    )
    missing_receipts = Experiment("x", "h", "observe", {}, True, True)
    valid_receipts = Experiment(
        "x", "h", "observe", {}, True, True,
        "auth-receipt", "sandbox-attestation",
    )
    forged_receipt = Experiment(
        "x", "h", "observe", {}, True, True,
        "forged", "sandbox-attestation",
    )
    assert not engine.approve_experiment(missing_receipts)
    assert not engine.approve_experiment(forged_receipt)
    assert engine.approve_experiment(valid_receipts)


def test_assessment_counts_unknowns_and_graph_evidence():
    ev = EvidenceRecord("e1", "dynamic", "fixture", "observed")
    assessment = SURFEngine().assess(_graph((ev,), "unknown"), ())
    assert assessment.graph_valid
    assert assessment.evidence_count == 1
    assert assessment.verified_evidence_count == 0
    assert assessment.unknowns == 1


def test_assessment_rejects_unrelated_external_evidence():
    graph_evidence = EvidenceRecord("e1", "static", "fixture", "observed")
    unrelated = EvidenceRecord("e2", "static", "other", "unrelated")
    assessment = SURFEngine().assess(_graph((graph_evidence,)), (unrelated,))
    assert not assessment.graph_valid
    assert assessment.evidence_count == 0


def test_malformed_hypotheses_and_candidates_do_not_inflate_trust():
    ev = EvidenceRecord("e1", "static", "fixture", "observed")
    malformed_hypothesis = HypothesisRecord("", "", status="verified")
    malformed_candidate = ImprovementCandidate("", "", verified=True, regression_passed=True)
    assessment = SURFEngine().assess(
        _graph((ev,)), (ev,), (malformed_hypothesis,), candidates=(malformed_candidate,)
    )
    assert assessment.graph_valid
    assert assessment.verified_hypotheses == 0
    assert not assessment.improvement_ready


def test_verified_status_alone_does_not_count_as_verified_hypothesis():
    ev = EvidenceRecord("e1", "static", "fixture", "observed", provenance="untrusted")
    hypothesis = HypothesisRecord("h1", "component uses protocol X", ("e1",), "verified")
    assessment = SURFEngine().assess(
        _graph((ev,)),
        (ev,),
        (hypothesis,),
    )
    assert assessment.verified_hypotheses == 0
    assert assessment.verified_evidence_count == 0


def test_hypothesis_counts_only_after_independent_evidence_and_hypothesis_verification():
    ev = EvidenceRecord("e1", "static", "fixture", "component observed", provenance="signed-fixture")
    hypothesis = HypothesisRecord("h1", "component uses protocol X", ("e1",), "verified")
    engine = SURFEngine(
        evidence_verifier=lambda evidence, graph: evidence.provenance == "signed-fixture",
        hypothesis_verifier=lambda item, graph, verified_ids: item.hypothesis_id == "h1" and "e1" in verified_ids,
    )

    assessment = engine.assess(_graph((ev,)), (ev,), (hypothesis,))

    assert assessment.verified_evidence_count == 1
    assert assessment.verified_hypotheses == 1


def test_only_receipt_verified_candidate_is_ready():
    ev = EvidenceRecord("e1", "static", "fixture", "observed")
    candidate = ImprovementCandidate(
        "c1", "meets requirements", (), True, True,
        "candidate-receipt", "regression-receipt",
    )
    engine = SURFEngine(
        candidate_verifier=lambda item, graph, evidence_ids: item.verification_receipt == "candidate-receipt",
        regression_verifier=lambda item, graph: item.regression_receipt == "regression-receipt",
    )
    assessment = engine.assess(_graph((ev,)), (ev,), candidates=(candidate,))
    assert assessment.improvement_ready


def test_candidate_boolean_flags_without_independent_receipts_are_not_ready():
    ev = EvidenceRecord("e1", "static", "fixture", "observed")
    candidate = ImprovementCandidate("c1", "meets requirements", (), True, True)
    assessment = SURFEngine().assess(_graph((ev,)), (ev,), candidates=(candidate,))
    assert not assessment.improvement_ready


def test_surf_contracts_bound_text_and_reject_arbitrary_experiment_values():
    oversized = EvidenceRecord("e1", "static", "fixture", "x" * 5000)
    assert not oversized.is_well_formed()
    arbitrary = Experiment("x", "h", "observe", {"payload": object()})
    non_finite = Experiment("x", "h", "observe", {"payload": float("nan")})
    assert not arbitrary.is_well_formed()
    assert not non_finite.is_well_formed()


def test_surf_experiment_values_have_a_depth_limit():
    value = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": "too deep"}}}}}}}}}
    experiment = Experiment("x", "h", "observe", value)
    assert not experiment.is_well_formed()


def test_assessment_rejects_malformed_or_duplicate_experiments():
    graph = _graph()
    malformed = Experiment("x", "h", "observe", {"value": object()})
    assert not SURFEngine().assess(graph, experiments=(malformed,)).graph_valid
    duplicate = Experiment("x", "h", "observe")
    assert not SURFEngine().assess(graph, experiments=(duplicate, duplicate)).graph_valid


def test_assessment_rejects_duplicate_hypothesis_and_candidate_ids():
    ev = EvidenceRecord("e1", "static", "fixture", "observed", provenance="signed")
    hypothesis = HypothesisRecord("h1", "claim", ("e1",), "verified")
    engine = SURFEngine(
        evidence_verifier=lambda evidence, graph: True,
        hypothesis_verifier=lambda item, graph, verified: True,
    )
    assert not engine.assess(_graph((ev,)), (ev,), (hypothesis, hypothesis)).graph_valid

    candidate = ImprovementCandidate("c1", "candidate", (), True, True, "v", "r")
    candidate_engine = SURFEngine(
        candidate_verifier=lambda item, graph, evidence: True,
        regression_verifier=lambda item, graph: True,
    )
    assert not candidate_engine.assess(
        _graph((ev,)), (ev,), candidates=(candidate, candidate)
    ).graph_valid
