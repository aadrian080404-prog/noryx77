import pytest

from core.device import CapabilityGrant, DeviceCapabilityGate, DeviceIdentity, DeviceRuntimeBoundary, DeviceTrust
from core.egress import EgressPolicy
from core.platform import AssistantIntegrationBoundary, PlatformKind

from .adapters import CapabilityAdapter, PlatformExecutionAdapter
from .capabilities import Capability, CapabilityBroker
from .contracts import ActionEnvelope


def envelope(**overrides):
    values = {
        "execution_id": "exec-1",
        "principal_id": "principal-1",
        "step_id": "step-1",
        "action_type": "read",
        "target": "memory",
        "parameters": {},
        "nonce": "nonce-1",
    }
    values.update(overrides)
    return ActionEnvelope(**values)


def test_adapter_resolves_exactly_one_capability():
    seen = []
    broker = CapabilityBroker({
        "memory": Capability("memory", frozenset({"read"}), lambda item: seen.append(item) or "ok")
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    assert adapter.execute(envelope()) == "ok"
    assert len(seen) == 1


def test_adapter_rejects_missing_identity_before_capability_resolution():
    broker = CapabilityBroker({
        "memory": Capability("memory", frozenset({"read"}), lambda item: "unsafe")
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    with pytest.raises(PermissionError):
        adapter.execute(envelope(principal_id=""))


def test_adapter_fails_closed_when_capability_is_ambiguous():
    broker = CapabilityBroker({
        "one": Capability("one", frozenset({"read"}), lambda item: "one"),
        "two": Capability("two", frozenset({"read"}), lambda item: "two"),
    })
    adapter = CapabilityAdapter(broker, agent_id="agent-1")

    with pytest.raises(LookupError):
        adapter.execute(envelope())


class FakePlatform:
    platform = PlatformKind.ANDROID

    def __init__(self):
        self.executed = []

    def execute(self, action):
        self.executed.append(action)
        return True


def platform_adapter(*, agent_id="agent-1", egress_policy=None):
    identity = DeviceIdentity("phone", "android", trust=DeviceTrust.VERIFIED)
    gate = DeviceCapabilityGate(identity)
    gate.grant(CapabilityGrant("network.request", "phone", 1000, 3))
    gate.grant(CapabilityGrant("notification", "phone", 1000, 3))
    boundary = AssistantIntegrationBoundary(device_boundary=DeviceRuntimeBoundary(gate))
    platform = FakePlatform()
    adapter = PlatformExecutionAdapter(platform, boundary, agent_id=agent_id, epoch=3, clock=lambda: 10, egress_policy=egress_policy)
    return adapter, platform


def network_envelope(**overrides):
    return envelope(
        action_type="network.request",
        target="network",
        parameters={"host": "api.example.com", "port": 443, "protocol": "tcp"},
        **overrides,
    )


def test_network_platform_action_requires_explicit_egress_policy():
    adapter, platform = platform_adapter()
    with pytest.raises(PermissionError, match="egress_policy_required"):
        adapter.execute(network_envelope())
    assert not platform.executed


def test_allowed_egress_reaches_platform_after_gate():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = platform_adapter(egress_policy=policy)

    assert adapter.execute(network_envelope()) is True
    assert len(platform.executed) == 1


def test_denied_egress_stops_before_platform_side_effect():
    policy = EgressPolicy()
    policy.allow("agent-1", "other.example.com", 443, "tcp")
    adapter, platform = platform_adapter(egress_policy=policy)

    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(network_envelope())
    assert not platform.executed


def test_egress_rule_cannot_be_reused_by_another_agent():
    policy = EgressPolicy()
    policy.allow("agent-2", "api.example.com", 443, "tcp")
    adapter, platform = platform_adapter(agent_id="agent-1", egress_policy=policy)

    with pytest.raises(PermissionError, match="egress_denied"):
        adapter.execute(network_envelope())
    assert not platform.executed


def test_host_suffix_port_protocol_and_malformed_destination_fail_closed():
    policy = EgressPolicy()
    policy.allow("agent-1", "api.example.com", 443, "tcp")
    adapter, platform = platform_adapter(egress_policy=policy)

    bad = (
        {"host": "api.example.com.attacker", "port": 443, "protocol": "tcp"},
        {"host": "api.example.com", "port": 8443, "protocol": "tcp"},
        {"host": "api.example.com", "port": 443, "protocol": "udp"},
        {"host": "api.example.com", "port": "443", "protocol": "tcp"},
    )
    for parameters in bad:
        with pytest.raises(PermissionError):
            adapter.execute(network_envelope(parameters=parameters))
    assert not platform.executed


def test_non_network_platform_action_uses_device_boundary_without_egress():
    adapter, platform = platform_adapter()
    assert adapter.execute(envelope(action_type="notification", target="device", parameters={"message": "ok"})) is True
    assert len(platform.executed) == 1
