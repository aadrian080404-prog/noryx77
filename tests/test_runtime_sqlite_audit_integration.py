import hashlib

from core.continuity import node_attestation_statement
from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog
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


def test_runtime_and_ncp_use_durable_sqlite_audit_across_restart(tmp_path):
    audit_path = tmp_path / "runtime-audit.sqlite3"
    identity_path = tmp_path / "node-trust.sqlite3"
    audit = SQLiteAuditLog(audit_path)
    runtime = NORYXRuntime(audit_log=audit)
    registry = SQLiteIdentityRegistry(identity_path)
    identity, private_key = AgentIdentityAuthority.generate("durable-runtime-node")
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
    supervisor.heartbeat(
        node_id=identity.agent_id,
        generation=0,
        sequence=1,
        attestation=_signed(identity, private_key, generation=0, sequence=1),
    )

    assert runtime.audit is audit
    assert runtime.hypersynth.audit is audit
    assert audit.verify_integrity()

    reopened = SQLiteAuditLog(audit_path)
    events = reopened.snapshot()
    assert [item["event"] for item in events] == [
        "continuity_supervisor_configured",
        "continuity_node_registered",
        "continuity_node_heartbeat",
    ]
    assert reopened.verify_integrity()


def test_runtime_configuration_does_not_publish_continuity_if_durable_audit_fails(tmp_path):
    audit = SQLiteAuditLog(tmp_path / "runtime-audit.sqlite3")
    runtime = NORYXRuntime(audit_log=audit)
    registry = SQLiteIdentityRegistry(tmp_path / "node-trust.sqlite3")

    def fail_record(*_args, **_kwargs):
        raise OSError("audit_unavailable")

    audit.record = fail_record
    try:
        runtime.configure_continuity(
            node_identity_registry=registry,
            approve_rejoin=lambda **_: True,
        )
    except OSError as exc:
        assert str(exc) == "audit_unavailable"
    else:
        raise AssertionError("continuity configuration should fail closed")
    assert runtime.continuity is None
