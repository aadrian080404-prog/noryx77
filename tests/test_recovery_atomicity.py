import threading

import pytest

from core.recovery import RecoveryController, RecoveryState


def test_run_if_normal_holds_recovery_lock_through_operation():
    recovery = RecoveryController()
    entered = threading.Event()
    release = threading.Event()
    transition_done = threading.Event()

    def operation():
        entered.set()
        assert not transition_done.wait(0.05)
        release.wait(1.0)
        return "ok"

    result = []

    worker = threading.Thread(target=lambda: result.append(recovery.run_if_normal(operation)))
    worker.start()
    assert entered.wait(1.0)

    transition = threading.Thread(target=lambda: (recovery.incident(), transition_done.set()))
    transition.start()
    assert not transition_done.wait(0.05)
    release.set()
    worker.join(1.0)
    transition.join(1.0)

    assert result == ["ok"]
    assert recovery.state is RecoveryState.INCIDENT
    assert recovery.epoch == 1


def test_stale_epoch_is_rejected_before_critical_operation():
    recovery = RecoveryController()
    _, epoch = recovery.snapshot()
    recovery.incident()
    called = False

    def operation():
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="recovery_state_denies_execution"):
        recovery.run_if_normal(operation, expected_epoch=epoch)
    assert called is False
