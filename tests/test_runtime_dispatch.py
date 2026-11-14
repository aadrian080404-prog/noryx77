import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.runtime_dispatch import dispatch


def authorize(principal_id: str, operation: str) -> bool:
    return principal_id == "principal-1" and operation == "run"


def test_runtime_dispatch_executes_only_allowed_topology():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    result = dispatch(
        intent,
        source=Front.ORCHESTRATION,
        target=Front.HYPERSYNTH,
        execution_id="e1",
        handler=lambda: "ok",
        authorize_principal=authorize,
    )
    assert result.receipt.accepted and result.value == "ok"
    assert result.receipt.principal_id == "principal-1"


def test_runtime_dispatch_fails_closed_for_lateral_topology():
    intent = make_intent(Front.JARVIS, "run", b"x", principal_id="principal-1")
    called = False

    def forbidden_handler():
        nonlocal called
        called = True
        return "bad"

    with pytest.raises(PermissionError):
        dispatch(
            intent,
            source=Front.JARVIS,
            target=Front.HYPERSYNTH,
            execution_id="e1",
            handler=forbidden_handler,
            authorize_principal=authorize,
        )
    assert called is False


def test_runtime_dispatch_rejects_source_spoof_before_handler():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    called = False

    def forbidden_handler():
        nonlocal called
        called = True
        return "bad"

    with pytest.raises(PermissionError):
        dispatch(
            intent,
            source=Front.JARVIS,
            target=Front.ORCHESTRATION,
            execution_id="e1",
            handler=forbidden_handler,
            authorize_principal=authorize,
        )
    assert called is False


def test_runtime_dispatch_rejects_unauthorized_principal_before_handler():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="revoked-principal")
    called = False

    def forbidden_handler():
        nonlocal called
        called = True
        return "bad"

    with pytest.raises(PermissionError, match="principal_not_authorized"):
        dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=Front.HYPERSYNTH,
            execution_id="e1",
            handler=forbidden_handler,
            authorize_principal=authorize,
        )
    assert called is False


def test_runtime_dispatch_contains_handler_failure():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    result = dispatch(
        intent,
        source=Front.ORCHESTRATION,
        target=Front.JARVIS,
        execution_id="e1",
        handler=lambda: (_ for _ in ()).throw(RuntimeError("x")),
        authorize_principal=authorize,
    )
    assert not result.receipt.accepted and result.value is None
