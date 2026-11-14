import pytest

from jarvis.core.recovery import RecoveryController, RecoveryState


def test_jarvis_recovery_is_explicit_and_monotonic():
    recovery = RecoveryController()
    assert recovery.snapshot() == (RecoveryState.NORMAL, 0)

    recovery.incident()
    recovery.lockdown()
    recovery.trusted_only()
    recovery.recover()
    recovery.verify(True)
    recovery.resume()

    assert recovery.state is RecoveryState.NORMAL
    assert recovery.epoch == 6


def test_jarvis_recovery_never_skips_verification():
    recovery = RecoveryController()
    recovery.incident()
    recovery.lockdown()
    recovery.trusted_only()
    recovery.recover()
    with pytest.raises(PermissionError, match="verification_required"):
        recovery.verify(False)
    assert recovery.state is RecoveryState.RECOVERY


def test_jarvis_guard_rejects_stale_epoch_without_calling_operation():
    recovery = RecoveryController()
    recovery.incident()
    called = False

    def operation():
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="recovery_state_denies_execution"):
        recovery.run_if_normal(operation, expected_epoch=0)
    assert called is False
