from core.surf_contracts import EvidenceRecord, SystemNode, SystemGraph, Experiment
from core.surf_engine import SURFEngine


def test_surf_graph_is_evidence_grounded():
    ev = EvidenceRecord("e1", "static", "fixture", "component observed", 0.9)
    node = SystemNode("n1", "component", "A", ("e1",))
    graph = SystemGraph("g1", (node,), (), (ev,))
    assert graph.is_well_formed()


def test_graph_rejects_missing_evidence():
    node = SystemNode("n1", "component", "A", ("missing",))
    assert not SystemGraph("g1", (node,), (), ()).is_well_formed()


def test_experiment_requires_authorization_and_sandbox():
    assert not SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, False, True))
    assert not SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, True, False))
    assert SURFEngine.approve_experiment(Experiment("x", "h", "observe", {}, True, True))


def test_assessment_counts_unknowns():
    ev = EvidenceRecord("e1", "dynamic", "fixture", "observed")
    node = SystemNode("n1", "component", "A", ("e1",), "unknown")
    graph = SystemGraph("g1", (node,), (), (ev,))
    assessment = SURFEngine().assess(graph, (ev,))
    assert assessment.unknowns == 1
