import pytest
from ecosystem.boundaries import Front, make_intent
from ecosystem.runtime_dispatch import dispatch
def test_runtime_dispatch_executes_only_allowed_topology():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x")
    result = dispatch(intent, source=Front.ORCHESTRATION, target=Front.HYPERSYNTH, execution_id="e1", handler=lambda: "ok")
    assert result.receipt.accepted and result.value == "ok"
def test_runtime_dispatch_fails_closed_for_lateral_topology():
    intent = make_intent(Front.JARVIS, "run", b"x")
    with pytest.raises(PermissionError):
        dispatch(intent, source=Front.JARVIS, target=Front.HYPERSYNTH, execution_id="e1", handler=lambda: "bad")
def test_runtime_dispatch_contains_handler_failure():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x")
    result = dispatch(intent, source=Front.ORCHESTRATION, target=Front.JARVIS, execution_id="e1", handler=lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert not result.receipt.accepted and result.value is None
