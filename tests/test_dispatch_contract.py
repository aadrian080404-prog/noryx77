import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.dispatch_contract import make_receipt


PRINCIPAL_ID = "principal-test"


def test_verified_dispatch_receipt_binds_intent_source_and_evidence():
    intent = make_intent(
        Front.ORCHESTRATION,
        "dispatch",
        b"payload",
        principal_id=PRINCIPAL_ID,
    )
    receipt = make_receipt(
        intent,
        source=Front.ORCHESTRATION,
        target=Front.HYPERSYNTH,
        execution_id="exec-1",
        accepted=True,
        reason="accepted",
        evidence=b"verified",
    )
    assert receipt.intent_id == intent.intent_id
    assert receipt.target is Front.HYPERSYNTH
    assert receipt.accepted is True
    assert receipt.principal_id == PRINCIPAL_ID


def test_cross_front_dispatch_rejects_source_spoofing_and_self_dispatch():
    intent = make_intent(
        Front.JARVIS,
        "execute",
        b"x",
        principal_id=PRINCIPAL_ID,
    )
    with pytest.raises(PermissionError, match="intent_source_mismatch"):
        make_receipt(
            intent,
            source=Front.BROWSER,
            target=Front.JARVIS,
            execution_id="exec-1",
            accepted=False,
            reason="denied",
            evidence=b"x",
        )
    with pytest.raises(ValueError, match="self_dispatch_denied"):
        make_receipt(
            intent,
            source=Front.JARVIS,
            target=Front.JARVIS,
            execution_id="exec-1",
            accepted=False,
            reason="denied",
            evidence=b"x",
        )
