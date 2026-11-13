import hashlib

from core.institutional_access import (
    AccessMode, InstitutionalAccessPolicy, InstitutionalApproval,
    InstitutionalMandate, InstitutionalRequest,
)


def build_request(mode=AccessMode.PREDICATE):
    return InstitutionalRequest("req-1", "agency-a", "IT", "fraud-investigation",
                                ("transaction:tx-1",), mode, 100.0)


def mandate_signature(mandate):
    statement = "|".join((mandate.mandate_id, mandate.institution_id, mandate.jurisdiction,
                          mandate.purpose, ",".join(mandate.permitted_scopes), str(mandate.expires_at)))
    return hashlib.sha256(statement.encode()).digest()


def build_mandate():
    unsigned = InstitutionalMandate("mandate-1", "agency-a", "IT", "fraud-investigation",
                                     ("transaction:tx-1",), 500.0, b"pending")
    return InstitutionalMandate(unsigned.mandate_id, unsigned.institution_id, unsigned.jurisdiction,
                                 unsigned.purpose, unsigned.permitted_scopes, unsigned.expires_at,
                                 mandate_signature(unsigned))


def approval_signature(approval):
    statement = "|".join((approval.approval_id, approval.approver_id,
                          approval.request_digest, str(approval.expires_at), approval.role))
    return hashlib.sha256(statement.encode()).digest()


def build_approvals(policy, request, count=2, supervisors=0):
    digest = policy.digest(request)
    approvals = []
    for i in range(count):
        role = "independent_supervisor" if i >= count - supervisors else "approver"
        unsigned = InstitutionalApproval(f"approval-{i}", f"reviewer-{i}", digest, 400.0, b"pending", role)
        approvals.append(InstitutionalApproval(
            unsigned.approval_id, unsigned.approver_id, unsigned.request_digest,
            unsigned.expires_at, approval_signature(unsigned), unsigned.role
        ))
    return tuple(approvals)


def make_policy():
    return InstitutionalAccessPolicy(
        mandate_verifier=lambda mandate: mandate.signature == mandate_signature(mandate),
        approval_verifier=lambda approval: approval.signature == approval_signature(approval),
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
        InstitutionalApproval("a1", "same-reviewer", policy.digest(request), 400.0, b"forged"),
        InstitutionalApproval("a2", "same-reviewer", policy.digest(request), 400.0, b"forged"),
    )
    assert not policy.evaluate(request, build_mandate(), duplicate, now=200.0).allowed
