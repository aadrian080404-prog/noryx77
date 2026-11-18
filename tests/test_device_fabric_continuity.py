import pytest

from core.continuity import ContinuitySupervisor, NodeContinuityState
from core.device_fabric import Device, DeviceFabric


def _supervisor():
    return ContinuitySupervisor(
        verify_attestation=lambda **_: True,
        approve_rejoin=lambda **_: True,
        audit=lambda *_: None,
    )


def _register_node(supervisor, node_id, fingerprint):
    return supervisor.register(
        node_id=node_id,
        identity_fingerprint=fingerprint * 64,
        capabilities=("compute", "memory"),
        attestation=b"test-attestation",
    )


def test_device_fabric_resolves_only_active_ncp_nodes():
    supervisor = _supervisor()
    _register_node(supervisor, "node-a", "a")
    _register_node(supervisor, "node-b", "b")
    fabric = DeviceFabric(continuity_supervisor=supervisor)
    fabric.register(Device("node-a", frozenset({"compute"})))
    fabric.register(Device("node-b", frozenset({"compute"})))

    assert fabric.resolve("compute").device_id == "node-a"
    supervisor.isolate("node-a", reason="heartbeat_failed")
    assert fabric.resolve("compute").device_id == "node-b"


def test_device_fabric_skips_trusted_but_offline_nodes():
    supervisor = _supervisor()
    _register_node(supervisor, "node-a", "a")
    _register_node(supervisor, "node-b", "b")
    fabric = DeviceFabric(continuity_supervisor=supervisor)
    fabric.register(Device("node-a", frozenset({"compute"})))
    fabric.register(Device("node-b", frozenset({"compute"}), online=False))

    assert fabric.resolve("compute").device_id == "node-a"
    fabric.set_online("node-a", False)
    with pytest.raises(LookupError, match="no_trusted_online_capable_device"):
        fabric.resolve("compute")


def test_device_fabric_never_selects_unattested_device_when_ncp_is_enabled():
    supervisor = _supervisor()
    fabric = DeviceFabric(continuity_supervisor=supervisor)
    fabric.register(Device("untrusted-device", frozenset({"compute"})))
    with pytest.raises(LookupError, match="no_trusted_online_capable_device"):
        fabric.resolve("compute")


def test_device_fabric_preserves_legacy_resolution_without_ncp():
    fabric = DeviceFabric()
    fabric.register(Device("legacy-device", frozenset({"compute"})))
    assert fabric.resolve("compute").device_id == "legacy-device"


def test_device_fabric_rejects_invalid_continuity_dependency():
    with pytest.raises(TypeError, match="invalid_continuity_supervisor"):
        DeviceFabric(continuity_supervisor=object())
