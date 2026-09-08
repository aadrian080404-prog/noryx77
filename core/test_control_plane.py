import pytest

from .control_plane import Noryx7ControlPlane
from .recovery import RecoveryState
from .supply_chain import SupplyChainVerifier
from .defense import DefenseMode


def test_control_plane_recovery_flow_is_synchronized_and_observed():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())
    assert control.status().recovery_state is RecoveryState.NORMAL
    assert control.status().defense_mode is DefenseMode.NORMAL
    assert control.status().event_count == 0

    control.incident()
    assert control.status().recovery_state is RecoveryState.TRUSTED_ONLY
    assert control.status().defense_mode is DefenseMode.LOCKDOWN
    assert control.status().event_count == 1

    control.begin_recovery()
    assert control.status().recovery_state is RecoveryState.RECOVERY
    assert control.status().defense_mode is DefenseMode.RECOVERY
    assert control.status().event_count == 2

    control.mark_verified()
    assert control.status().recovery_state is RecoveryState.VERIFIED
    assert control.status().defense_mode is DefenseMode.RESTRICTED
    assert control.status().event_count == 3

    control.resume_normal()
    assert control.status().recovery_state is RecoveryState.NORMAL
    assert control.status().defense_mode is DefenseMode.NORMAL
    assert control.status().event_count == 4
    events = control.events.snapshot()
    assert len(events) == 4
    assert all(len(event.evidence_digest) == 64 for event in events)
    assert [event.event_id for event in events] == [1, 2, 3, 4]


def test_control_plane_recovery_methods_fail_closed_on_wrong_state():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())
    with pytest.raises(PermissionError):
        control.begin_recovery()
    with pytest.raises(PermissionError):
        control.mark_verified()
    with pytest.raises(PermissionError):
        control.resume_normal()
    assert control.status().event_count == 0


def test_control_plane_detects_desynchronized_security_planes_before_transition():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())
    control.defense.enter_lockdown("test desynchronization")

    with pytest.raises(PermissionError, match="control_plane_state_desynchronized"):
        control.incident()

    # The recovery plane was not advanced after the mismatch was detected.
    assert control.recovery.snapshot() == (RecoveryState.NORMAL, 0)
    assert control.defense.mode is DefenseMode.LOCKDOWN
    assert control.status().event_count == 0
