import pytest

from .matrix_safety_gate import DurableSafetyGate


COMMAND = b"set-valve-target:closed"


def make_gate(tmp_path, *, allowed=True, interlock=True):
    return DurableSafetyGate(
        str(tmp_path / "safety.sqlite"),
        authorize_operator=lambda operator, _resource, _digest: allowed and operator in {"op-a", "op-b"},
        interlock_check=lambda _resource, _digest: interlock,
    )


def prepared_gate(tmp_path, *, allowed=True, interlock=True):
    gate = make_gate(tmp_path, allowed=allowed, interlock=interlock)
    gate.propose("proposal-1", "requester", "valve-7", COMMAND, 100, now=1)
    gate.approve("proposal-1", "op-a", now=2)
    gate.approve("proposal-1", "op-b", now=3)
    return gate


def test_critical_command_requires_two_distinct_approvals_and_one_time_permit(tmp_path):
    gate = make_gate(tmp_path)
    gate.propose("proposal-1", "requester", "valve-7", COMMAND, 100, now=1)
    with pytest.raises(PermissionError, match="two_distinct_approvals_required"):
        gate.issue("proposal-1", now=4)
    assert gate.approve("proposal-1", "op-a", now=2) == 1
    assert gate.approve("proposal-1", "op-b", now=3) == 2
    permit = gate.issue("proposal-1", now=4)
    assert gate.consume(permit, COMMAND, now=5)
    with pytest.raises(PermissionError, match="permit_invalid_or_already_consumed"):
        gate.consume(permit, COMMAND, now=6)


def test_proposer_cannot_approve_and_duplicate_approval_does_not_count_twice(tmp_path):
    gate = make_gate(tmp_path)
    gate.propose("p", "requester", "asset", COMMAND, 50, now=1)
    with pytest.raises(PermissionError, match="proposer_cannot_approve"):
        gate.approve("p", "requester", now=2)
    assert gate.approve("p", "op-a", now=2) == 1
    assert gate.approve("p", "op-a", now=3) == 1
    with pytest.raises(PermissionError, match="two_distinct_approvals_required"):
        gate.issue("p", now=4)


def test_operator_authorization_and_local_interlock_fail_closed(tmp_path):
    denied = make_gate(tmp_path, allowed=False)
    denied.propose("p", "requester", "asset", COMMAND, 50, now=1)
    with pytest.raises(PermissionError, match="operator_not_authorized"):
        denied.approve("p", "op-a", now=2)

    blocked = prepared_gate(tmp_path / "blocked", interlock=False)
    with pytest.raises(PermissionError, match="local_safety_interlock_blocked"):
        blocked.issue("proposal-1", now=4)


def test_permit_is_bound_to_resource_command_and_expiry(tmp_path):
    gate = prepared_gate(tmp_path)
    permit = gate.issue("proposal-1", now=4)
    with pytest.raises(PermissionError, match="permit_command_or_resource_mismatch"):
        gate.consume(permit, b"different-command", now=5)
    with pytest.raises(PermissionError, match="permit_expired_or_inactive"):
        gate.consume(permit, COMMAND, now=100)


def test_expired_proposal_cannot_be_approved_or_issued(tmp_path):
    gate = make_gate(tmp_path)
    gate.propose("p", "requester", "asset", COMMAND, 5, now=1)
    with pytest.raises(PermissionError, match="proposal_expired"):
        gate.approve("p", "op-a", now=5)
    assert gate is not None


def test_permit_is_not_consumed_if_interlock_fails_at_execution_boundary(tmp_path):
    gate = prepared_gate(tmp_path)
    permit = gate.issue("proposal-1", now=4)
    gate.interlock_check = lambda *_: False
    with pytest.raises(PermissionError, match="local_safety_interlock_blocked"):
        gate.consume(permit, COMMAND, now=5)
