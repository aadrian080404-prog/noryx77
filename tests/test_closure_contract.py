from ecosystem.closure_contract import CLOSURE_CONTRACTS, require_contract_shape
from ecosystem.completeness import evaluate


def test_cross_front_contract_covers_exactly_all_fronts():
    require_contract_shape()
    assert len(CLOSURE_CONTRACTS) == 4


def test_structural_gate_includes_closure_contract():
    complete, problems = evaluate()
    assert isinstance(complete, bool)
    assert isinstance(problems, tuple)
    assert all(isinstance(problem, str) and problem for problem in problems)
