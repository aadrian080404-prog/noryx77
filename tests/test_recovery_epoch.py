import pytest

from core.recovery import RecoveryController, RecoveryState


def test_recovery_epoch_changes_on_every_successful_transition():
    recovery = RecoveryController()
    assert recovery.snapshot() == (RecoveryState.NORMAL, 0)
    recovery.incident()
    assert recovery.snapshot() == (RecoveryState.INCIDENT, 1)
    recovery.lockdown()
    assert recovery.snapshot() == (RecoveryState.LOCKDOWN, 2)
    recovery.trusted_only()
    assert recovery.snapshot() == (RecoveryState.TRUSTED_ONLY, 3)
    recovery.recover()
    assert recovery.snapshot() == (RecoveryState.RECOVERY, 4)
    recovery.verify(True)
    assert recovery.snapshot() == (RecoveryState.VERIFIED, 5)
    recovery.resume()
    assert recovery.snapshot() == (RecoveryState.NORMAL, 6)


def test_stale_epoch_is_rejected():
    recovery = RecoveryController()
    _, epoch = recovery.snapshot()
    recovery.incident()
    with pytest.raises(PermissionError, match="recovery_state_denies_execution"):
        recovery.require_normal(expected_epoch=epoch)


def test_guard_serializes_operation_against_recovery_transitions():
    recovery = RecoveryController()
    seen = []

    def operation():
        seen.append(recovery.state)
        return "committed"

    assert recovery.run_if_normal(operation, expected_epoch=0) == "committed"
    assert seen == [RecoveryState.NORMAL]


def test_invalid_guard_operation_fails_closed():
    recovery = RecoveryController()
    with pytest.raises(TypeError, match="operation_required"):
        recovery.run_if_normal(None)
