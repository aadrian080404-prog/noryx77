from .control_plane import Noryx7ControlPlane
from .defense import DefenseMode
from .recovery import RecoveryState
from .supply_chain import SupplyChainVerifier


def test_security_transition_is_authoritative_when_observability_fails():
    control = Noryx7ControlPlane(supply_chain=SupplyChainVerifier())

    def broken_publish(*args, **kwargs):
        raise RuntimeError("observer_down")

    control.events.publish = broken_publish  # type: ignore[method-assign]
    control.incident()

    assert control.recovery.state is RecoveryState.TRUSTED_ONLY
    assert control.defense.mode is DefenseMode.LOCKDOWN
    assert control.observation_failures == 1
