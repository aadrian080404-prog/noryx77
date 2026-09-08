import pytest

from core.device import CapabilityGrant, DeviceCapabilityGate, DeviceIdentity, DeviceRuntimeBoundary, DeviceTrust
from core.egress import EgressPolicy
from core.platform import AssistantIntegrationBoundary, PlatformKind

from .adapters import PlatformExecutionAdapter
from .contracts import ActionEnvelope


class FakePlatform:
    platform = PlatformKind.ANDROID

    def __init__(self):
        self.executed = []

    def execute(self, action):
        self.executed.append(action)
        return True


def make_adapter(*, agent_id="agent-1", egress_policy=None):
    identity = DeviceIdentity("phone", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("network.request", "phone", 1000, 3))
    gate.grant(CapabilityGrant("notification", "phone", 1000, 3))
    boundary = AssistantIntegrationBoundary(device_boundary=DeviceRuntimeBoundary(gate))
    platform = FakePlatform()
    adapter = PlatformExecutionAdapter(platform, boundary, agent_id=agent_id, epoch=3, clock=lambda: 10, egress_policy=egress_policy)
    return adapter, platform


def envelope(**overrides):
    values = {
        "execution_id": "exec-1", "principal_id": "principal-1", "step_id": "step-1",
        "action_type": "network.request", "target": "network",
        "parameters": {"host": "api.example.com", "port": 443, "protocol": "tcp"}, "nonce": "nonce-1",
    }
    values.update(overrides)
    return ActionEnvelope(**values)


def test_network_action_requires_egress_policy():
    adapter, platform = make_adapter()
    with pytest.raises(PermissionError, match="egress_policy_required"):
        adapter.execute(envelope())
    assert not platform.executed


def test_allowed_egress_is_checked_before_platform_execution():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = make_adapter(egress_policy=policy)
    assert adapter.execute(envelope()) is True
    assert len(platform.executed) == 1


def test_denied_egress_blocks_platform_side_effect():
    policy = EgressPolicy()
    policy.allow("agent-1", "other.example.com", 443, "tcp")
    adapter, platform = make_adapter(egress_policy=policy)
    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(envelope())
    assert not platform.executed


def test_egress_is_bound_to_agent_component():
    policy = EgressPolicy()
    policy.allow("agent-2", "api.example.com", 443, "tcp")
    adapter, platform = make_adapter(agent_id="agent-1", egress_policy=policy)
    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(envelope())
    assert not platform.executed


def test_egress_canonicalization_does_not_allow_host_suffix_bypass():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = make_adapter(egress_policy=policy)
    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(envelope(parameters={"host": "api.example.com.attacker", "port": 443, "protocol": "tcp"}))
    assert not platform.executed


def test_egress_requires_exact_port_and_protocol():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = make_adapter(egress_policy=policy)
    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(envelope(parameters={"host": "api.example.com", "port": 8443, "protocol": "tcp"}))
    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(envelope(parameters={"host": "api.example.com", "port": 443, "protocol": "udp"}))
    assert not platform.executed


def test_malformed_destination_is_denied_before_platform_execution():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = make_adapter(egress_policy=policy)
    with pytest.raises(PermissionError, match="invalid_egress_destination"):
        adapter.execute(envelope(parameters={"host": "api.example.com", "port": "443", "protocol": "tcp"}))
    assert not platform.executed


def test_non_network_action_remains_platform_capability_gated():
    adapter, platform = make_adapter()
    action = envelope(action_type="notification", target="device", parameters={"message": "ok"})
    assert adapter.execute(action) is True
    assert len(platform.executed) == 1
