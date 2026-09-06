from core.device import CapabilityGrant, DeviceCapabilityGate, DeviceIdentity, DeviceRole, DeviceTrust


def test_capability_grant_cannot_follow_device_identity_swap():
    original = DeviceIdentity("device-a", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(original)
    gate.grant(CapabilityGrant("transfer", "device-a", expires_at=100, epoch=7))

    assert gate.allows("transfer", now=50, epoch=7)

    # DeviceIdentity is immutable, but the gate's live reference is intentionally
    # replaceable by integration code; the grant must remain bound to its audience.
    gate.identity = DeviceIdentity("device-b", "android", DeviceRole.CLIENT, DeviceTrust.VERIFIED)
    assert not gate.allows("transfer", now=50, epoch=7)
