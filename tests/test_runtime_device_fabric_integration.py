import hashlib

import pytest

from core.continuity import node_attestation_statement
from core.device_fabric import Device
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.runtime import NORYXRuntime


def _signed(identity, private_key, *, generation=0, sequence=0):
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    statement = node_attestation_statement(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        generation=generation,
        sequence=sequence,
    )
    return AgentIdentityAuthority.sign(identity, private_key, statement)


def test_runtime_wires_existing_devices_to_ncp_fencing():
    runtime = NORYXRuntime()
    runtime.device_fabric.register(Device("compute-node", frozenset({"compute"})))

    registry = IdentityRegistry()
    identity, private_key = AgentIdentityAuthority.generate("compute-node")
    registry.register(identity)
    supervisor = runtime.configure_continuity(
        node_identity_registry=registry,
        approve_rejoin=lambda **_: True,
    )
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    supervisor.register(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        capabilities=("compute",),
        attestation=_signed(identity, private_key),
    )

    assert runtime.device_fabric.resolve("compute").device_id == "compute-node"
    supervisor.isolate("compute-node", reason="test_isolation")
    with pytest.raises(LookupError, match="no_trusted_online_capable_device"):
        runtime.device_fabric.resolve("compute")


def test_runtime_rejects_replacing_configured_continuity_supervisor():
    runtime = NORYXRuntime()
    registry = IdentityRegistry()
    first, _ = AgentIdentityAuthority.generate("first-node")
    registry.register(first)
    runtime.configure_continuity(
        node_identity_registry=registry,
        approve_rejoin=lambda **_: True,
    )

    with pytest.raises(RuntimeError, match="continuity_already_configured"):
        runtime.configure_continuity(
            node_identity_registry=registry,
            approve_rejoin=lambda **_: True,
        )
