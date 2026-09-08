import pytest

from core.actions import ActionSpec
from core.policy import PolicyEngine
from core.recovery import RecoveryController, RecoveryState
from core.security import SecurityBoundary
from core.verification import VerificationEngine


def _boundary():
    return SecurityBoundary(PolicyEngine(), VerificationEngine(), RecoveryController())


def test_security_denies_every_action_outside_normal_recovery_state():
    boundary = _boundary()
    action = ActionSpec("recovery-test", "compute", risk_class="normal")

    boundary.recovery.incident()
    assert boundary.recovery.state is RecoveryState.INCIDENT
    assert not boundary.inspect(action).allowed

    boundary.recovery.lockdown()
    assert not boundary.inspect(action).allowed
    boundary.recovery.trusted_only()
    assert not boundary.inspect(action).allowed
    boundary.recovery.recover()
    assert not boundary.inspect(action).allowed


def test_security_resumes_only_after_explicit_recovery_verification():
    boundary = _boundary()
    action = ActionSpec("recovery-test", "compute", risk_class="normal")

    boundary.recovery.incident()
    boundary.recovery.lockdown()
    boundary.recovery.trusted_only()
    boundary.recovery.recover()

    with pytest.raises(PermissionError, match="verification_required"):
        boundary.recovery.verify(False)
    assert boundary.recovery.state is RecoveryState.RECOVERY
    assert not boundary.inspect(action).allowed

    boundary.recovery.verify(True)
    assert boundary.recovery.state is RecoveryState.VERIFIED
    assert not boundary.inspect(action).allowed

    boundary.recovery.resume()
    assert boundary.recovery.state is RecoveryState.NORMAL
    assert boundary.inspect(action).allowed


def test_security_rejects_invalid_recovery_controller():
    with pytest.raises(TypeError, match="invalid_recovery_controller"):
        SecurityBoundary(PolicyEngine(), VerificationEngine(), recovery=object())
