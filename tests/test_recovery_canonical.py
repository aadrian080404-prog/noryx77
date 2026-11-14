from core.recovery import RecoveryController as CanonicalRecoveryController
from jarvis.core.recovery import RecoveryController as JarvisRecoveryController
from jarvis.core.recovery import RecoveryState as JarvisRecoveryState


def test_jarvis_uses_canonical_recovery_controller():
    assert JarvisRecoveryController is CanonicalRecoveryController


def test_jarvis_recovery_state_is_canonical():
    from core.recovery import RecoveryState

    assert JarvisRecoveryState is RecoveryState
