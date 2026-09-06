import pytest

from .control_plane import Noryx7ControlPlane
from .recovery import RecoveryState
from .supply_chain import SupplyChainVerifier
from .defense import DefenseMode


def test_control_plane_recovery_flow_is_synchronized():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())
    assert control.status().recovery_state is RecoveryState.NORMAL
    assert control.status().defense_mode is DefenseMode.NORMAL

    control.incident()
    assert control.status().recovery_state is RecoveryState.TRUSTED_ONLY
    assert control.status().defense_mode is DefenseMode.LOCKDOWN

    control.begin_recovery()
    assert control.status().recovery_state is RecoveryState.RECOVERY
    assert control.status().defense_mode is DefenseMode.RECOVERY

    control.mark_verified()
    assert control.status().recovery_state is RecoveryState.VERIFIED
    assert control.status().defense_mode is DefenseMode.RESTRICTED

    control.resume_normal()
    assert control.status().recovery_state is RecoveryState.NORMAL
    assert control.status().defense_mode is DefenseMode.NORMAL


def test_control_plane_recovery_methods_fail_closed_on_wrong_state():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())
    with pytest.raises(PermissionError):
        control.begin_recovery()
    with pytest.raises(PermissionError):
        control.mark_verified()
    with pytest.raises(PermissionError):
        control.resume_normal()
