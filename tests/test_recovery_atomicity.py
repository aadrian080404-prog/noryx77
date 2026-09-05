import threading

import pytest

from core.recovery import RecoveryController, RecoveryState


def test_run_if_normal_serializes_recovery_transition_until_operation_finishes():
    recovery = RecoveryController()
    started = threading.Event()
    release = threading.Event()
    transition_finished = threading.Event()

    def operation():
        started.set()
        assert recovery.state is RecoveryState.NORMAL
        assert recovery.epoch == 0
        release.wait(timeout=2)
        assert recovery.state is RecoveryState.NORMAL
        return "committed"

    result = {}

    def worker():
        result["value"] = recovery.run_if_normal(operation, expected_epoch=0)

    def transition():
        started.wait(timeout=2)
        recovery.incident()
        transition_finished.set()

    worker_thread = threading.Thread(target=worker)
    transition_thread = threading.Thread(target=transition)
    worker_thread.start()
    assert started.wait(timeout=2)
    transition_thread.start()

    # The incident cannot interleave with the guarded critical section.
    assert not transition_finished.wait(timeout=0.1)
    release.set()
    worker_thread.join(timeout=2)
    transition_thread.join(timeout=2)

    assert result["value"] == "committed"
    assert transition_finished.is_set()
    assert recovery.state is RecoveryState.INCIDENT
    assert recovery.epoch == 1


def test_run_if_normal_rejects_stale_epoch_before_operation():
    recovery = RecoveryController()
    recovery.incident()
    called = False

    def operation():
        nonlocal called
        called = True

    with pytest.raises(PermissionError, match="recovery_state_denies_execution"):
        recovery.run_if_normal(operation, expected_epoch=0)
    assert called is False
