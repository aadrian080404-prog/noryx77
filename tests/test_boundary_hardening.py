import pytest

from ecosystem.boundaries import Front, make_intent
from ecosystem.dispatch_contract import make_receipt


def test_intent_rejects_oversized_payload():
    with pytest.raises(ValueError, match="payload_size_exceeded"):
        make_intent(Front.ORCHESTRATION, "run", b"x" * (4 * 1024 * 1024 + 1))


def test_receipt_rejects_blank_reason_and_oversized_evidence():
    intent = make_intent(Front.ORCHESTRATION, "run", b"x")
    with pytest.raises(ValueError, match="invalid_reason"):
        make_receipt(
            intent,
            source=Front.ORCHESTRATION,
            target=Front.JARVIS,
            execution_id="e",
            accepted=False,
            reason=" ",
            evidence=b"x",
        )
    with pytest.raises(ValueError, match="evidence_size_exceeded"):
        make_receipt(
            intent,
            source=Front.ORCHESTRATION,
            target=Front.JARVIS,
            execution_id="e",
            accepted=False,
            reason="denied",
            evidence=b"x" * (64 * 1024 + 1),
        )
