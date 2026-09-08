import pytest

from .cyber_range import AttackPhase, CyberRange, OwnerAuthorization, SyntheticTarget


def make_range():
    value = CyberRange(max_actions=8)
    value.register_target(SyntheticTarget("lab-01", ("CVE-SIM-001",)))
    return value


def test_simulation_requires_owner_authorization():
    value = make_range()
    with pytest.raises(PermissionError, match="owner_authorization_required"):
        value.simulate(target_id="lab-01", principal_id="owner", authorization=OwnerAuthorization("other", "a", 99), now=1, techniques=("recon",))


def test_expired_authorization_is_rejected():
    value = make_range()
    auth = OwnerAuthorization("owner", "a", 10)
    with pytest.raises(PermissionError, match="owner_authorization_required"):
        value.simulate(target_id="lab-01", principal_id="owner", authorization=auth, now=11, techniques=("recon",))


def test_only_sandbox_targets_are_accepted():
    with pytest.raises(ValueError, match="sandbox"):
        SyntheticTarget("real-host", trust_zone="internet")


def test_simulation_is_symbolic_and_verified():
    value = make_range()
    report = value.simulate(
        target_id="lab-01", principal_id="owner",
        authorization=OwnerAuthorization("owner", "a", 99), now=1,
        techniques=("enumerate_services", "exploit_simulation", "privilege_escalation_simulation"),
    )
    assert report.verified is True
    assert all(action.target_id == "lab-01" for action in report.actions)
    assert AttackPhase.EXPLOIT_SIMULATION in {action.phase for action in report.actions}
