import dataclasses

import pytest

from core.institutional_access import (
    AccessMode,
    AccessRequest,
    Approval,
    InstitutionalAccessGate,
    Mandate,
)


class TestVerifier:
    def verify_mandate(self, issuer_id, payload, signature):
        return signature == b"valid"

    def verify_approval(self, approver_id, payload, signature):
        return signature == b"valid"


def setup_case(**request_changes):
    mandate = Mandate(
        mandate_id="mandate-1",
        case_id="case-1",
        jurisdiction="IT",
        purpose="fraud-investigation",
        allowed_data_scopes=("transaction:aggregate", "identity:predicate"),
        valid_from=90.0,
        expires_at=200.0,
        issuer_id="issuer-1",
        signature=b"valid",
    )
    request = AccessRequest(
        request_id="request-1",
        mandate=mandate,
        jurisdiction="IT",
        purpose="fraud-investigation",
        data_scopes=("transaction:aggregate",),
        mode=AccessMode.AGGREGATE,
        created_at=100.0,
        output_limit=10,
    )
    request = dataclasses.replace(request, **request_changes)
    gate = InstitutionalAccessGate(
        verifier=TestVerifier(),
        trusted_approvers={
            "authority-a": ("domain-a", "authorization"),
            "oversight-b": ("domain-b", "oversight"),
            "authority-c": ("domain-c", "authorization"),
        },
        required_approvals=2,
        required_roles=("authorization", "oversight"),
        max_output_limit=20,
        clock=lambda: 110.0,
    )
    digest = gate.request_digest(request)
    approvals = (
        Approval("authority-a", digest, "authorization", 105.0, b"valid"),
        Approval("oversight-b", digest, "oversight", 106.0, b"valid"),
    )
    return gate, request, approvals


def test_valid_request_authorizes_only_a_plan():
    gate, request, approvals = setup_case()
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is True
    assert decision.reason == "authorized_plan_only"
    assert decision.approved_scopes == ("transaction:aggregate",)
    assert decision.approver_domains == ("domain-a", "domain-b")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"purpose": "unrelated-purpose"}, "purpose_mismatch"),
        ({"jurisdiction": "US"}, "jurisdiction_mismatch"),
        ({"data_scopes": ("medical:raw",)}, "scope_exceeds_mandate"),
        ({"output_limit": 21}, "output_limit_exceeded"),
        ({"mode": "NArKoS"}, "unsupported_access_mode"),
    ],
)
def test_request_scope_and_mode_are_fail_closed(changes, reason):
    gate, request, approvals = setup_case(**changes)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == reason


def test_mandate_signature_is_required():
    gate, request, approvals = setup_case()
    changed = dataclasses.replace(request, mandate=dataclasses.replace(request.mandate, signature=b"bad"))
    decision = gate.evaluate(changed, approvals)
    assert decision.allowed is False
    assert decision.reason == "invalid_mandate_signature"


def test_approvals_are_bound_to_exact_request():
    gate, request, approvals = setup_case()
    changed = dataclasses.replace(request, output_limit=9)
    decision = gate.evaluate(changed, approvals)
    assert decision.allowed is False
    assert decision.reason == "approval_binding_invalid"


def test_same_independence_domain_cannot_form_quorum():
    gate, request, approvals = setup_case()
    gate = InstitutionalAccessGate(
        verifier=TestVerifier(),
        trusted_approvers={
            "authority-a": ("same-domain", "authorization"),
            "oversight-b": ("same-domain", "oversight"),
        },
        required_approvals=2,
        required_roles=("authorization", "oversight"),
        clock=lambda: 110.0,
    )
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "approver_independence_violation"


def test_untrusted_approver_is_rejected():
    gate, request, approvals = setup_case()
    digest = gate.request_digest(request)
    changed = (Approval("unknown", digest, "authorization", 105.0, b"valid"), approvals[1])
    decision = gate.evaluate(request, changed)
    assert decision.allowed is False
    assert decision.reason == "untrusted_approver"


def test_expired_mandate_is_rejected():
    gate, request, approvals = setup_case()
    expired = dataclasses.replace(request.mandate, expires_at=109.0)
    changed = dataclasses.replace(request, mandate=expired)
    decision = gate.evaluate(changed, approvals)
    assert decision.allowed is False
    assert decision.reason == "mandate_expired_or_not_yet_valid"


def test_verifier_outage_fails_closed():
    class BrokenVerifier:
        def verify_mandate(self, issuer_id, payload, signature):
            raise RuntimeError("offline")

        def verify_approval(self, approver_id, payload, signature):
            raise RuntimeError("offline")

    gate, request, approvals = setup_case()
    gate = InstitutionalAccessGate(
        verifier=BrokenVerifier(),
        trusted_approvers={
            "authority-a": ("domain-a", "authorization"),
            "oversight-b": ("domain-b", "oversight"),
        },
        required_approvals=2,
        required_roles=("authorization", "oversight"),
        clock=lambda: 110.0,
    )
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "mandate_verification_unavailable"


def test_boolean_timestamps_are_rejected():
    gate, request, approvals = setup_case(created_at=True)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "invalid_time"


def test_numeric_overflow_in_timestamp_fails_closed():
    gate, request, approvals = setup_case()
    request = dataclasses.replace(request, created_at=10 ** 10000)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False


def test_clock_exception_fails_closed():
    gate, request, approvals = setup_case()
    gate = InstitutionalAccessGate(
        verifier=TestVerifier(),
        trusted_approvers={
            "authority-a": ("domain-a", "authorization"),
            "oversight-b": ("domain-b", "oversight"),
        },
        required_approvals=2,
        required_roles=("authorization", "oversight"),
        clock=lambda: (_ for _ in ()).throw(RuntimeError("clock offline")),
    )
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "clock_unavailable"


def test_impossible_quorum_configuration_is_rejected():
    with pytest.raises(ValueError, match="invalid_required_roles_or_quorum"):
        InstitutionalAccessGate(
            verifier=TestVerifier(),
            trusted_approvers={"a": ("domain-a", "authorization")},
            required_approvals=2,
            required_roles=("authorization",),
            clock=lambda: 110.0,
        )


def test_approval_digest_binds_full_mandate_contents():
    gate, request, approvals = setup_case()
    changed_mandate = dataclasses.replace(
        request.mandate,
        allowed_data_scopes=("transaction:aggregate", "identity:predicate", "new-scope"),
    )
    changed_request = dataclasses.replace(request, mandate=changed_mandate)
    decision = gate.evaluate(changed_request, approvals)
    assert decision.allowed is False
    assert decision.reason == "approval_binding_invalid"


def test_predicate_mode_has_single_result_output_limit():
    gate, request, approvals = setup_case(mode=AccessMode.PREDICATE, output_limit=2)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "output_limit_exceeded"


def test_supervised_mode_requires_an_independent_supervisor():
    gate, request, approvals = setup_case(mode=AccessMode.SUPERVISED)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "independent_approval_quorum_not_met"


def test_supervised_mode_requires_and_accepts_third_role_and_domain():
    mandate = Mandate(
        "mandate-2", "case-2", "IT", "fraud-investigation",
        ("transaction:aggregate",), 90.0, 200.0, "issuer-1", b"valid",
    )
    request = AccessRequest(
        "request-2", mandate, "IT", "fraud-investigation",
        ("transaction:aggregate",), AccessMode.SUPERVISED, 100.0, 10,
    )
    gate = InstitutionalAccessGate(
        verifier=TestVerifier(),
        trusted_approvers={
            "authority-a": ("domain-a", "authorization"),
            "oversight-b": ("domain-b", "oversight"),
            "supervisor-c": ("domain-c", "independent_supervisor"),
        },
        required_approvals=2,
        required_roles=("authorization", "oversight"),
        clock=lambda: 110.0,
    )
    digest = gate.request_digest(request)
    approvals = (
        Approval("authority-a", digest, "authorization", 105.0, b"valid"),
        Approval("oversight-b", digest, "oversight", 106.0, b"valid"),
        Approval("supervisor-c", digest, "independent_supervisor", 107.0, b"valid"),
    )
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is True
    assert decision.approver_domains == ("domain-a", "domain-b", "domain-c")


def test_approval_count_is_bounded():
    gate, request, approvals = setup_case()
    oversized = approvals + tuple(
        Approval("authority-a", approvals[0].request_digest, "authorization", 107.0, b"valid")
        for _ in range(63)
    )
    decision = gate.evaluate(request, oversized)
    assert decision.allowed is False
    assert decision.reason == "approval_limit_exceeded"
