import pytest

from .device import (
    CapabilityGrant,
    DeviceAction,
    DeviceCapabilityGate,
    DeviceIdentity,
    DeviceRole,
    DeviceRuntimeBoundary,
    DeviceTrust,
)


def test_device_requires_verified_identity_and_epoch_bound_grant():
    identity = DeviceIdentity("phone-1", "android", DeviceRole.CLIENT, DeviceTrust.UNKNOWN)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("notify", "phone-1", 100, 7))
    boundary = DeviceRuntimeBoundary(gate)
    action = DeviceAction("phone-1", "notify", "push", 7)
    assert not boundary.authorize(action, now=10, epoch=7)

    gate.identity = DeviceIdentity("phone-1", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    assert boundary.authorize(action, now=10, epoch=7)
    assert not boundary.authorize(action, now=101, epoch=7)
    assert not boundary.authorize(action, now=10, epoch=8)


def test_grant_cannot_be_replayed_to_another_device():
    gate = DeviceCapabilityGate(DeviceIdentity("phone-a", "android"))
    with pytest.raises(PermissionError):
        gate.grant(CapabilityGrant("camera", "phone-b", 100, 1))


def test_action_cannot_target_another_device():
    identity = DeviceIdentity("phone-a", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("camera", "phone-a", 100, 1))
    boundary = DeviceRuntimeBoundary(gate)
    assert not boundary.authorize(DeviceAction("phone-b", "camera", "capture", 1), now=1, epoch=1)


def test_capability_revocation_is_immediate():
    identity = DeviceIdentity("phone-a", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("microphone", "phone-a", 100, 1))
    assert gate.allows("microphone", now=1, epoch=1)
    gate.revoke("microphone")
    assert not gate.allows("microphone", now=1, epoch=1)
