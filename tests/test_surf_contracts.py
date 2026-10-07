from core.surf_contracts import *

def test_surf_graph_is_evidence_grounded():
    ev=EvidenceRecord("e1","static","fixture","component observed",0.9)
    n=SystemNode("n1","component","A",("e1",))
    g=SystemGraph("g1",(n,),(),(ev,))
    assert g.is_well_formed()

def test_graph_rejects_missing_evidence():
    n=SystemNode("n1","component","A",("missing",))
    assert not SystemGraph("g1",(n,),(),()).is_well_formed()

def test_experiment_requires_authorization_and_sandbox():
    assert not SURFEngine.approve_experiment(Experiment("x","h","observe",{},False,True))
    assert not SURFEngine.approve_experiment(Experiment("x","h","observe",{},True,False))
    assert SURFEngine.approve_experiment(Experiment("x","h","observe",{},True,True))

def test_assessment_counts_unknowns():
    ev=EvidenceRecord("e1","dynamic","fixture","observed")
    n=SystemNode("n1","component","A",("e1",),"unknown")
    g=SystemGraph("g1",(n,),(),(ev,))
    a=SURFEngine().assess(g,(ev,))
    assert a.unknowns == 1
