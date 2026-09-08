from ecosystem.global_closure import evaluate, require_closed


def test_global_infrastructure_closure_passes():
    report = evaluate()
    assert report.passed, report.problems
    require_closed()
