import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.runtime_wiring import FrontAdapter, RuntimeWiring


def _wiring(calls):
    return RuntimeWiring({
        front: FrontAdapter(front, lambda operation, payload, execution_id, front=front: calls.append((front, operation, payload, execution_id)) or front.value)
        for front in Front
    })


def test_requires_all_four_fronts():
    with pytest.raises(ValueError, match="all_four_front_adapters_required"):
        RuntimeWiring({Front.ORCHESTRATION: FrontAdapter(Front.ORCHESTRATION, lambda *_: None)})


def test_cross_front_invocation_enters_through_orchestration():
    calls = []
    wiring = _wiring(calls)
    result = wiring.invoke_target(Front.JARVIS, "execute", b"payload", execution_id="exec-1")
    assert result.receipt.accepted is True
    assert calls == [(Front.JARVIS, "execute", b"payload", "exec-1")]


def test_invoke_requires_original_payload_for_non_orchestration_target():
    calls = []
    wiring = _wiring(calls)
    intent = make_intent(Front.JARVIS, "execute", b"payload")
    with pytest.raises(ValueError, match="original_payload_required"):
        wiring.invoke(intent, execution_id="exec-1")
    assert calls == []


def test_invoke_rejects_payload_digest_mismatch_before_dispatch():
    calls = []
    wiring = _wiring(calls)
    intent = make_intent(Front.JARVIS, "execute", b"payload")
    with pytest.raises(PermissionError, match="intent_payload_digest_mismatch"):
        wiring.invoke(intent, execution_id="exec-1", payload=b"tampered")
    assert calls == []


def test_invoke_preserves_original_payload_digest():
    calls = []
    wiring = _wiring(calls)
    payload = b"payload"
    intent = make_intent(Front.JARVIS, "execute", payload)
    result = wiring.invoke(intent, execution_id="exec-1", payload=payload)
    assert result.receipt.accepted is True
    assert calls == [(Front.JARVIS, "execute", payload, "exec-1")]


def test_orchestration_cannot_be_called_as_target():
    wiring = _wiring([])
    with pytest.raises(PermissionError, match="orchestration_must_enter_via_invoke"):
        wiring.invoke_target(Front.ORCHESTRATION, "dispatch", b"payload", execution_id="exec-1")
