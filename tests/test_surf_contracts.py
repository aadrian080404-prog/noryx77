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


def test_experiment_requires_authorization_and_sandbox():
    assert not SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, False, True))
    assert not SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, True, False))
    assert SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, True, True))


def test_assessment_counts_unknowns_and_graph_evidence():
    ev = EvidenceRecord("e1", "dynamic", "fixture", "observed")
    assessment = SURFEngine().assess(_graph((ev,), "unknown"), ())
    assert assessment.graph_valid
    assert assessment.evidence_count == 1
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


def test_only_well_formed_verified_candidate_is_ready():
    ev = EvidenceRecord("e1", "static", "fixture", "observed")
    candidate = ImprovementCandidate("c1", "meets requirements", (), True, True)
    assessment = SURFEngine().assess(_graph((ev,)), (ev,), candidates=(candidate,))
    assert assessment.improvement_ready
