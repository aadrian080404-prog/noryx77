import hashlib

import pytest

from core.audit import AuditLog
from core.continuity import node_attestation_statement
from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime
from core.sqlite_identity import SQLiteIdentityRegistry


def _signed(identity, private_key, *, generation, sequence):
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    statement = node_attestation_statement(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        generation=generation,
        sequence=sequence,
    )
    return AgentIdentityAuthority.sign(identity, private_key, statement)


def test_runtime_uses_injected_audit_log_for_hypersynth_and_continuity(tmp_path):
    audit = AuditLog()
    runtime = NORYXRuntime(audit_log=audit)
    registry = SQLiteIdentityRegistry(tmp_path / "trusted-nodes.sqlite3")
    identity, private_key = AgentIdentityAuthority.generate("runtime-node")
    registry.register(identity)

    supervisor = runtime.configure_continuity(
        node_identity_registry=registry,
        approve_rejoin=lambda **_: True,
    )
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    admitted = supervisor.register(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        capabilities=("compute",),
        attestation=_signed(identity, private_key, generation=0, sequence=0),
    )
    supervisor.heartbeat(
        node_id=identity.agent_id,
        generation=0,
        sequence=1,
        attestation=_signed(identity, private_key, generation=0, sequence=1),
    )

    assert runtime.audit is audit
    assert runtime.hypersynth.audit is audit
    assert runtime.continuity is supervisor
    assert admitted.state.value == "active"
    assert [entry["event"] for entry in audit.snapshot()] == [
        "continuity_supervisor_configured",
        "continuity_node_registered",
        "continuity_node_heartbeat",
    ]
    assert audit.verify_integrity()


def test_runtime_continuity_rejects_revoked_node_and_records_isolation(tmp_path):
    runtime = NORYXRuntime(audit_log=AuditLog())
    registry = SQLiteIdentityRegistry(tmp_path / "trusted-nodes.sqlite3")
    identity, private_key = AgentIdentityAuthority.generate("revocable-runtime-node")
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
        attestation=_signed(identity, private_key, generation=0, sequence=0),
    )

    registry.revoke(identity.agent_id)
    with pytest.raises(PermissionError, match="node_heartbeat_rejected"):
        supervisor.heartbeat(
            node_id=identity.agent_id,
            generation=0,
            sequence=1,
            attestation=_signed(identity, private_key, generation=0, sequence=1),
        )

    assert supervisor.snapshot()[0].state.value == "isolated"
    assert runtime.audit.snapshot()[-1]["event"] == "continuity_node_isolated"


def test_runtime_continuity_requires_explicit_trust_and_rejoin_approval():
    runtime = NORYXRuntime()
    with pytest.raises(TypeError, match="node_identity_registry_required"):
        runtime.configure_continuity(
            node_identity_registry=object(),
            approve_rejoin=lambda **_: True,
        )
    with pytest.raises(TypeError, match="rejoin_approval_callback_required"):
        runtime.configure_continuity(
            node_identity_registry=runtime.identity_registry,
            approve_rejoin=None,
        )
