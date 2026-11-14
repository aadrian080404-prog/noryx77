import pytest

from noryx7_runtime.contracts import ExecutionStatus
from noryx7_runtime.lifecycle import ExecutionLifecycle, LifecycleError


def test_created_execution_can_start_and_complete():
    lifecycle = ExecutionLifecycle("exec-1", "principal-1")
    running = lifecycle.transition(ExecutionStatus.RUNNING)
    done = running.transition(ExecutionStatus.SUCCEEDED)
    assert lifecycle.status is ExecutionStatus.CREATED
    assert running.status is ExecutionStatus.RUNNING
    assert done.status is ExecutionStatus.SUCCEEDED
    assert done.terminal


def test_terminal_execution_cannot_transition():
    lifecycle = ExecutionLifecycle("exec-1", "principal-1", ExecutionStatus.FAILED)
    with pytest.raises(LifecycleError): lifecycle.transition(ExecutionStatus.RUNNING)


def test_created_execution_can_be_rejected_or_cancelled_but_not_succeeded():
    lifecycle = ExecutionLifecycle("exec-1", "principal-1")
    assert lifecycle.can_transition(ExecutionStatus.REJECTED)
    assert lifecycle.can_transition(ExecutionStatus.CANCELLED)
    assert not lifecycle.can_transition(ExecutionStatus.SUCCEEDED)


def test_running_execution_can_reject_fail_or_cancel_but_cannot_return_to_created():
    lifecycle = ExecutionLifecycle("exec-1", "principal-1", ExecutionStatus.RUNNING)
    assert not lifecycle.can_transition(ExecutionStatus.CREATED)
    assert lifecycle.can_transition(ExecutionStatus.REJECTED)
    assert lifecycle.can_transition(ExecutionStatus.FAILED)
    assert lifecycle.can_transition(ExecutionStatus.CANCELLED)


def test_identity_is_required_and_state_is_immutable():
    with pytest.raises(LifecycleError): ExecutionLifecycle("", "principal-1")
    with pytest.raises(LifecycleError): ExecutionLifecycle("exec-1", "")
    lifecycle = ExecutionLifecycle("exec-1", "principal-1")
    assert lifecycle.status is ExecutionStatus.CREATED
    assert lifecycle.transition(ExecutionStatus.CANCELLED).status is ExecutionStatus.CANCELLED
