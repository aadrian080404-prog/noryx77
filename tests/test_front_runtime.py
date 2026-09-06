import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.front_runtime import hypersynth


class Runtime:
    def run(self, task, interaction_context):
        return {"status":"completed","task":task,"context":interaction_context}


def test_hypersynth_adapter_binds_concrete_runtime_to_dispatch():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    result = hypersynth(intent, "e1", Runtime(), "task", "ctx")
    assert result.receipt.accepted
    assert result.receipt.principal_id == "principal-1"
    assert result.value["status"] == "completed"


def test_dispatch_requires_principal_identity():
    from ecosystem.boundaries import IntentEnvelope
    from ecosystem.runtime_dispatch import dispatch
    with pytest.raises(ValueError, match="principal_id_invalid"):
        IntentEnvelope("i", Front.ORCHESTRATION, "run", "0" * 64, "")


def test_dispatch_rejects_source_identity_mismatch_before_handler():
    from ecosystem.runtime_dispatch import dispatch
    intent = make_intent(Front.ORCHESTRATION, "run", b"x", principal_id="principal-1")
    called = False

    def handler():
        nonlocal called
        called = True
        return "should-not-run"

    with pytest.raises(PermissionError, match="intent_source_mismatch"):
        dispatch(intent, source=Front.JARVIS, target=Front.HYPERSYNTH, execution_id="e1", handler=handler)
    assert not called
