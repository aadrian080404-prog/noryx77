from ecosystem.completeness import evaluate


def test_unified_structural_gate_is_complete():
    complete, problems = evaluate()
    assert complete, problems
