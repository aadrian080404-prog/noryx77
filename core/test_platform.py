from .device import CapabilityGrant, DeviceCapabilityGate, DeviceIdentity, DeviceTrust
from .platform import (
    AssistantIntegrationBoundary,
    InteractionKind,
    PlatformAction,
    PlatformKind,
    PlatformRequest,
)


class FakeAdapter:
    platform = PlatformKind.ANDROID

    def __init__(self):
        self.executed = []

    def receive(self):
        return PlatformRequest("r1", "phone", PlatformKind.ANDROID, InteractionKind.TEXT, "hello")

    def execute(self, action):
        self.executed.append(action)
        return True


def test_platform_action_requires_device_capability_and_current_epoch():
    identity = DeviceIdentity("phone", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("notification", "phone", 100, 3))
    boundary = AssistantIntegrationBoundary(device_boundary=__import__("core.device", fromlist=["DeviceRuntimeBoundary"]).DeviceRuntimeBoundary(gate))
    adapter = FakeAdapter()
    action = PlatformAction("notify", "phone", "notification", "ok", 3)
    assert boundary.execute(adapter, action, now=10, epoch=3)
    assert len(adapter.executed) == 1
    assert not boundary.execute(adapter, action, now=10, epoch=4)


def test_platform_cannot_execute_on_wrong_device():
    identity = DeviceIdentity("phone", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("notification", "phone", 100, 1))
    boundary = AssistantIntegrationBoundary(device_boundary=__import__("core.device", fromlist=["DeviceRuntimeBoundary"]).DeviceRuntimeBoundary(gate))
    adapter = FakeAdapter()
    action = PlatformAction("notify", "other", "notification", "ok", 1)
    assert not boundary.execute(adapter, action, now=10, epoch=1)
    assert not adapter.executed
