import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.front_runtime import hypersynth
from ecosystem.runtime_dispatch import dispatch


class Runtime:
    def run(self, task, interaction_context):
        return {"status": "completed", "task": task, "context": interaction_context}


def authorize(principal_id: str, operation: str) -> bool:
    return principal_id == "principal-1" and operation == "run"


def test_hypersynth_adapter_binds_concrete_runtime_to_dispatch():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    result = hypersynth(
        intent, "e1", Runtime(), "task", "ctx", authorize_principal=authorize
    )
    assert result.receipt.accepted
    assert result.receipt.principal_id == "principal-1"
    assert result.value["status"] == "completed"


def test_dispatch_requires_principal_identity():
    from ecosystem.boundaries import IntentEnvelope

    with pytest.raises(ValueError, match="principal_id_invalid"):
        IntentEnvelope("i", Front.ORCHESTRATION, "run", "0" * 64, "")


def test_dispatch_rejects_source_identity_mismatch_before_authorization_and_handler():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    called = False
    authorized = False

    def authorize_spy(principal_id: str, operation: str) -> bool:
        nonlocal authorized
        authorized = True
        return authorize(principal_id, operation)

    def handler():
        nonlocal called
        called = True
        return "should-not-run"

    with pytest.raises(PermissionError, match="intent_source_mismatch"):
        dispatch(
            intent,
            source=Front.JARVIS,
            target=Front.HYPERSYNTH,
            execution_id="e1",
            handler=handler,
            authorize_principal=authorize_spy,
        )
    assert not authorized
    assert not called


def test_front_adapter_rejects_unauthorized_principal_before_handler():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="revoked")
    called = False

    class GuardedRuntime(Runtime):
        def run(self, task, interaction_context):
            nonlocal called
            called = True
            return super().run(task, interaction_context)

    with pytest.raises(PermissionError, match="principal_not_authorized"):
        hypersynth(
            intent, "e1", GuardedRuntime(), "task", "ctx", authorize_principal=authorize
        )
    assert not called


def test_dispatch_fails_closed_when_authorizer_raises():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    called = False

    def broken_authorizer(principal_id: str, operation: str) -> bool:
        raise RuntimeError("authorization service unavailable")

    def handler():
        nonlocal called
        called = True
        return "should-not-run"

    with pytest.raises(PermissionError, match="principal_not_authorized"):
        dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=Front.HYPERSYNTH,
            execution_id="e1",
            handler=handler,
            authorize_principal=broken_authorizer,
        )
    assert not called


def test_dispatch_authorizer_receives_exact_principal_and_operation():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    calls = []

    def recording_authorizer(principal_id: str, operation: str) -> bool:
        calls.append((principal_id, operation))
        return True

    result = dispatch(
        intent,
        source=Front.ORCHESTRATION,
        target=Front.HYPERSYNTH,
        execution_id="e1",
        handler=lambda: "ok",
        authorize_principal=recording_authorizer,
    )

    assert result.receipt.accepted
    assert calls == [("principal-1", "run")]


def test_dispatch_requires_authorizer():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    with pytest.raises(TypeError, match="principal_authorizer_required"):
        dispatch(
            intent,
            source=Front.ORCHESTRATION,
            target=Front.HYPERSYNTH,
            execution_id="e1",
            handler=lambda: "should-not-run",
            authorize_principal=None,
        )
