import pytest
from ecosystem.boundaries import Front, make_intent
from ecosystem.dispatch_contract import make_receipt
from ecosystem.isolation import allows_dispatch

def test_only_orchestration_can_initiate_cross_front_work():
    assert allows_dispatch(Front.ORCHESTRATION, Front.JARVIS)
    assert allows_dispatch(Front.ORCHESTRATION, Front.BROWSER)
    assert allows_dispatch(Front.ORCHESTRATION, Front.HYPERSYNTH)
    assert not allows_dispatch(Front.JARVIS, Front.HYPERSYNTH)
    assert not allows_dispatch(Front.BROWSER, Front.JARVIS)

def test_lateral_dispatch_is_fail_closed():
    intent = make_intent(Front.JARVIS, "x", b"x")
    with pytest.raises(PermissionError, match="cross_front_dispatch_denied"):
        make_receipt(intent, source=Front.JARVIS, target=Front.HYPERSYNTH,
                     execution_id="e1", accepted=True, reason="x", evidence=b"x")
