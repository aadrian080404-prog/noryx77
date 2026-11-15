import pytest

from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_durable import DurableFencedResource


def conditions(**overrides):
    values = dict(
        battery_percent=80, temperature_c=35, estimated_power_watts=3,
        minute_of_week=100, network_bps_available=10_000_000,
    )
    values.update(overrides)
    return DeviceConditions(**values)


def policy(**overrides):
    values = dict(
        enabled=True, minimum_battery_percent=40, maximum_temperature_c=42,
        maximum_power_watts=5, maximum_network_bps=1_000_000,
        remaining_energy_wh=10, allowed_windows=((0, 200),),
    )
    values.update(overrides)
    return DeviceContributionPolicy(**values)


def test_device_contribution_is_off_by_default():
    allowed, reason = DeviceContributionPolicy().permits(conditions(), 1)
    assert not allowed and reason == "contribution_not_enabled"


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        ({"battery_percent": 20}, "battery_below_owner_threshold"),
        ({"temperature_c": 50}, "device_temperature_above_limit"),
        ({"estimated_power_watts": 8}, "power_above_owner_limit"),
        ({"network_bps_available": 1}, "insufficient_network_capacity"),
        ({"minute_of_week": 500}, "outside_owner_schedule"),
    ],
)
def test_device_policy_blocks_unsafe_or_unconsented_conditions(state, reason):
    allowed, actual = policy().permits(conditions(**state), 1)
    assert not allowed and actual == reason


def test_device_policy_enforces_energy_budget_and_allows_valid_work():
    allowed, reason = policy().permits(conditions(), 2)
    assert allowed and reason == "permitted"
    allowed, reason = policy(remaining_energy_wh=5).permits(conditions(), 2)
    assert not allowed and reason == "energy_budget_exhausted"


def test_device_policy_supports_weekly_window_crossing_sunday():
    sunday_night = 10000
    p = policy(allowed_windows=((9900, 100),))
    assert p.permits(conditions(minute_of_week=sunday_night), 1)[0]
    assert p.permits(conditions(minute_of_week=50), 1)[0]
    assert not p.permits(conditions(minute_of_week=500), 1)[0]


def test_durable_fencing_survives_reopen_and_namespaces_operations(tmp_path):
    db = tmp_path / "matrix.db"
    resource = DurableFencedResource(db, "device:relay-1")
    resource.activate(1)
    first = resource.apply(1, "tenant-a", "op-1", b"open")
    assert first.version == 1

    reopened = DurableFencedResource(db, "device:relay-1")
    assert reopened.highest_token == 1
    assert reopened.version == 1
    assert reopened.apply(1, "tenant-a", "op-1", b"open") == first
    second = reopened.apply(1, "tenant-b", "op-1", b"open")
    assert second.version == 2


def test_durable_fencing_rejects_stale_epoch_after_restart(tmp_path):
    db = tmp_path / "matrix.db"
    old = DurableFencedResource(db, "resource")
    old.activate(4)
    old.apply(4, "tenant", "op-1", b"write")
    new = DurableFencedResource(db, "resource")
    new.activate(5)
    with pytest.raises(PermissionError, match="stale_or_unactivated_fencing_token"):
        old.apply(4, "tenant", "op-2", b"stale")
    assert new.apply(5, "tenant", "op-2", b"current").version == 2


def test_durable_fencing_rejects_idempotency_payload_conflict(tmp_path):
    resource = DurableFencedResource(tmp_path / "matrix.db", "resource")
    resource.activate(1)
    resource.apply(1, "tenant", "same", b"first")
    with pytest.raises(PermissionError, match="idempotency_key_payload_conflict"):
        resource.apply(1, "tenant", "same", b"different")


def test_durable_fencing_rejects_non_monotonic_activation(tmp_path):
    resource = DurableFencedResource(tmp_path / "matrix.db", "resource")
    resource.activate(2)
    with pytest.raises(PermissionError, match="fencing_token_not_monotonic"):
        resource.activate(2)
