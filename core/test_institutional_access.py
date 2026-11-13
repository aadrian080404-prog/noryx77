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


def setup_case(
    *,
    approval_replay_guard=None,
    require_durable_approval_replay=False,
    require_authenticated_approval_replay=False,
    **request_changes,
):
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
        approval_replay_guard=approval_replay_guard,
        require_durable_approval_replay=require_durable_approval_replay,
        require_authenticated_approval_replay=require_authenticated_approval_replay,
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


from core.authorization_replay import (
    AuthenticatedAuthorizationReplayGuard,
    AuthorizationReplayGuard,
)


def test_institutional_approvals_are_consumed_once_as_an_atomic_batch():
    guard = AuthorizationReplayGuard(max_tokens=8)
    gate, request, approvals = setup_case(approval_replay_guard=guard)
    first = gate.evaluate(request, approvals)
    second = gate.evaluate(request, approvals)
    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "approval_replay_or_capacity_rejected"
    assert guard.consumed_count == 2


def test_institutional_approval_batch_is_all_or_none_on_capacity():
    guard = AuthorizationReplayGuard(max_tokens=1)
    gate, request, approvals = setup_case(approval_replay_guard=guard)
    decision = gate.evaluate(request, approvals)
    assert decision.allowed is False
    assert decision.reason == "approval_replay_or_capacity_rejected"
    assert guard.consumed_count == 0


def test_institutional_approval_replay_persists_across_restart(tmp_path):
    path = str(tmp_path / "institutional-approval-replay.sqlite")
    first_guard = AuthorizationReplayGuard(path=path, max_tokens=8)
    gate, request, approvals = setup_case(
        approval_replay_guard=first_guard,
        require_durable_approval_replay=True,
    )
    assert gate.evaluate(request, approvals).allowed is True
    first_guard.close()

    second_guard = AuthorizationReplayGuard(path=path, max_tokens=8)
    reopened_gate, _, _ = setup_case(
        approval_replay_guard=second_guard,
        require_durable_approval_replay=True,
    )
    replay = reopened_gate.evaluate(request, approvals)
    assert replay.allowed is False
    assert replay.reason == "approval_replay_or_capacity_rejected"
    second_guard.close()


def test_high_assurance_institutional_gate_requires_authenticated_replay(tmp_path):
    path = str(tmp_path / "institutional-authenticated-replay.sqlite")
    guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"i" * 32,
        key_id="institutional-replay-key",
        path=path,
        max_tokens=8,
    )
    gate, request, approvals = setup_case(
        approval_replay_guard=guard,
        require_authenticated_approval_replay=True,
    )
    assert gate.approval_replay_durable is True
    assert gate.approval_replay_integrity_protected is True
    assert gate.evaluate(request, approvals).allowed is True
    guard.close()


def test_institutional_gate_refuses_unkeyed_store_for_authenticated_replay(tmp_path):
    guard = AuthorizationReplayGuard(
        path=str(tmp_path / "unkeyed-institutional-replay.sqlite"),
        max_tokens=8,
    )
    with pytest.raises(ValueError, match="authenticated_approval_replay_guard_required"):
        setup_case(
            approval_replay_guard=guard,
            require_authenticated_approval_replay=True,
        )
    guard.close()


def test_institutional_gate_requires_durable_guard_when_requested():
    with pytest.raises(ValueError, match="durable_approval_replay_guard_required"):
        setup_case(require_durable_approval_replay=True)


def test_institutional_quorum_overlap_cannot_reuse_one_approver_signature():
    guard = AuthorizationReplayGuard(max_tokens=8)
    gate, request, approvals = setup_case(approval_replay_guard=guard)
    assert gate.evaluate(request, approvals).allowed is True

    digest = gate.request_digest(request)
    # Reuse the same signed oversight proof in a different otherwise-valid quorum.
    overlapping = (
        Approval("authority-c", digest, "authorization", 105.0, b"valid"),
        approvals[1],
    )
    replay = gate.evaluate(request, overlapping)
    assert replay.allowed is False
    assert replay.reason == "approval_replay_or_capacity_rejected"
    # The new authority-c token was not partially consumed when the reused
    # oversight-b token caused the atomic batch to fail.
    assert guard.consumed_count == 2
