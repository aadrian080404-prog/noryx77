from core.institutional_access import (
    AccessMode, InstitutionalAccessPolicy, InstitutionalApproval,
    InstitutionalMandate, InstitutionalRequest,
)


def build_request(mode=AccessMode.PREDICATE):
    return InstitutionalRequest("req-1", "agency-a", "IT", "fraud-investigation",
                                ("transaction:tx-1",), mode, 100.0)


def build_mandate():
    return InstitutionalMandate("mandate-1", "agency-a", "IT", "fraud-investigation",
                                ("transaction:tx-1",), 500.0, b"mandate-signature")


def build_approvals(policy, request, count=2, supervisors=0):
    digest = policy.digest(request)
    return tuple(
        InstitutionalApproval(
            f"approval-{i}", f"reviewer-{i}", digest, 400.0,
            b"approval-signature",
            "independent_supervisor" if i >= count - supervisors else "approver",
        )
        for i in range(count)
    )


def make_policy():
    return InstitutionalAccessPolicy(
        mandate_verifier=lambda mandate: mandate.signature == b"mandate-signature",
        approval_verifier=lambda approval: approval.signature == b"approval-signature",
    )


def test_valid_request_is_policy_authorized_without_releasing_data():
    policy = make_policy()
    request = build_request()
    decision = policy.evaluate(request, build_mandate(), build_approvals(policy, request), now=200.0)
    assert decision.allowed
    assert decision.reason == "policy_authorized_only_no_data_released"


def test_scope_escalation_is_denied():
    policy = make_policy()
    request = InstitutionalRequest("req-1", "agency-a", "IT", "fraud-investigation",
                                   ("all-customer-data",), AccessMode.PREDICATE, 100.0)
    decision = policy.evaluate(request, build_mandate(), build_approvals(policy, request), now=200.0)
    assert not decision.allowed


def test_request_bound_approvals_cannot_be_replayed_for_another_request():
    policy = make_policy()
    original = build_request()
    approvals = build_approvals(policy, original)
    changed = InstitutionalRequest("req-2", "agency-a", "IT", "fraud-investigation",
                                   ("transaction:tx-1",), AccessMode.PREDICATE, 100.0)
    decision = policy.evaluate(changed, build_mandate(), approvals, now=200.0)
    assert not decision.allowed


def test_supervised_reconstruction_requires_additional_approval():
    policy = make_policy()
    request = build_request(AccessMode.SUPERVISED_RECONSTRUCTION)
    decision = policy.evaluate(request, build_mandate(), build_approvals(policy, request, 2), now=200.0)
    assert not decision.allowed
    assert decision.required_approvals == 3
    decision = policy.evaluate(request, build_mandate(), build_approvals(policy, request, 3), now=200.0)
    assert not decision.allowed
    decision = policy.evaluate(request, build_mandate(), build_approvals(policy, request, 3, supervisors=1), now=200.0)
    assert decision.allowed


def test_expired_or_duplicate_approvals_are_denied():
    policy = make_policy()
    request = build_request()
    duplicate = (
        InstitutionalApproval("a1", "same-reviewer", policy.digest(request), 400.0, b"approval-signature"),
        InstitutionalApproval("a2", "same-reviewer", policy.digest(request), 400.0, b"approval-signature"),
    )
    assert not policy.evaluate(request, build_mandate(), duplicate, now=200.0).allowed
