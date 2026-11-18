import hashlib

import pytest

from core.continuity import (
    ContinuitySupervisor,
    NodeContinuityState,
    agent_identity_attestation_verifier,
    audit_log_sink,
    node_attestation_statement,
)
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.audit import AuditLog


def make_supervisor(*, audit=None, approve=True, verify=True):
    events = []
    def verifier(**_):
        return verify
    def approver(**_):
        return approve
    def sink(event, payload):
        if audit is not None:
            audit(event, payload)
        events.append((event, payload))
    supervisor = ContinuitySupervisor(
        verify_attestation=verifier,
        approve_rejoin=approver,
        audit=sink,
        max_nodes=2,
    )
    return supervisor, events


def register(supervisor, node_id="node-a"):
    return supervisor.register(
        node_id=node_id,
        identity_fingerprint="a" * 64,
        capabilities=("compute", "memory"),
        attestation=b"signed-attestation",
    )


def test_registration_requires_valid_attestation():
    supervisor, _ = make_supervisor(verify=False)
    with pytest.raises(PermissionError, match="node_attestation_rejected"):
        register(supervisor)
    assert supervisor.snapshot() == ()


def test_heartbeat_sequence_is_monotonic_and_stale_replay_isolates_node():
    supervisor, _ = make_supervisor()
    register(supervisor)
    active = supervisor.heartbeat(
        node_id="node-a", generation=0, sequence=1, attestation=b"heartbeat-1"
    )
    assert active.state is NodeContinuityState.ACTIVE
    with pytest.raises(PermissionError, match="node_heartbeat_rejected"):
        supervisor.heartbeat(
            node_id="node-a", generation=0, sequence=1, attestation=b"replayed"
        )
    assert supervisor.snapshot()[0].state is NodeContinuityState.ISOLATED
    with pytest.raises(LookupError, match="no_trusted_active_node"):
        supervisor.resolve("compute")


def test_rejoin_requires_new_generation_attestation_and_approval():
    supervisor, _ = make_supervisor()
    register(supervisor)
    supervisor.isolate("node-a", reason="operator_requested")
    with pytest.raises(PermissionError, match="node_rejoin_approval_required"):
        denied, _ = make_supervisor(approve=False)
        register(denied)
        denied.isolate("node-a", reason="operator_requested")
        denied.rejoin(
            node_id="node-a", generation=1, sequence=0,
            attestation=b"fresh-attestation", approval="not-approved",
        )
    restored = supervisor.rejoin(
        node_id="node-a", generation=1, sequence=0,
        attestation=b"fresh-attestation", approval="human-approved",
    )
    assert restored.state is NodeContinuityState.ACTIVE
    assert restored.generation == 1
    with pytest.raises(PermissionError, match="node_heartbeat_rejected"):
        supervisor.heartbeat(
            node_id="node-a", generation=0, sequence=99, attestation=b"old-generation"
        )


def test_audit_failure_during_heartbeat_fences_node():
    audit_state = {"fail": False}
    def broken_audit(_event, _payload):
        if audit_state["fail"]:
            raise OSError("audit unavailable")
    supervisor, _ = make_supervisor(audit=broken_audit)
    register(supervisor)
    audit_state["fail"] = True
    with pytest.raises(OSError, match="audit unavailable"):
        supervisor.heartbeat(
            node_id="node-a", generation=0, sequence=1, attestation=b"heartbeat"
        )
    assert supervisor.snapshot()[0].state is NodeContinuityState.ISOLATED


def test_resolution_is_deterministic_and_capacity_is_bounded():
    supervisor, _ = make_supervisor()
    register(supervisor, "node-z")
    register(supervisor, "node-a")
    assert supervisor.resolve("compute").node_id == "node-a"
    with pytest.raises(OverflowError, match="continuity_node_capacity_exceeded"):
        register(supervisor, "node-c")



def test_ncp_attestation_uses_existing_ed25519_identity_registry():
    registry = IdentityRegistry()
    identity, private_key = AgentIdentityAuthority.generate("node-signed")
    registry.register(identity)
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    statement = node_attestation_statement(
        node_id="node-signed", identity_fingerprint=fingerprint,
        generation=0, sequence=0,
    )
    attestation = AgentIdentityAuthority.sign(identity, private_key, statement)
    supervisor = ContinuitySupervisor(
        verify_attestation=agent_identity_attestation_verifier(registry),
        approve_rejoin=lambda **_: True,
        audit=lambda *_: None,
    )
    admitted = supervisor.register(
        node_id="node-signed", identity_fingerprint=fingerprint,
        capabilities=("compute",), attestation=attestation,
    )
    assert admitted.state is NodeContinuityState.ACTIVE


def test_ncp_ed25519_attestation_is_bound_to_generation_and_sequence():
    registry = IdentityRegistry()
    identity, private_key = AgentIdentityAuthority.generate("node-bound")
    registry.register(identity)
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    supervisor = ContinuitySupervisor(
        verify_attestation=agent_identity_attestation_verifier(registry),
        approve_rejoin=lambda **_: True,
        audit=lambda *_: None,
    )
    with pytest.raises(PermissionError, match="node_attestation_rejected"):
        supervisor.register(
            node_id="node-bound", identity_fingerprint=fingerprint,
            node_id="node-bound", identity_fingerprint=fingerprint,
            capabilities=("compute",),
            attestation=AgentIdentityAuthority.sign(
                identity, private_key,
                node_attestation_statement(
                    node_id="node-bound", identity_fingerprint=fingerprint,
                    generation=1, sequence=0,
                ),
            ),
        )


def test_ncp_attestation_rejects_revoked_identity():
    registry = IdentityRegistry()
    identity, private_key = AgentIdentityAuthority.generate("node-revoked")
    registry.register(identity)
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    signed = AgentIdentityAuthority.sign(
        identity, private_key,
        node_attestation_statement(
            node_id="node-revoked", identity_fingerprint=fingerprint,
            generation=0, sequence=0,
        ),
    )
    registry.revoke("node-revoked")
    verifier = agent_identity_attestation_verifier(registry)
    assert verifier(
        node_id="node-revoked", identity_fingerprint=fingerprint,
        generation=0, sequence=0, attestation=signed,
    ) is False



def test_ncp_events_are_written_through_native_audit_log_contract():
    audit = AuditLog()
    supervisor = ContinuitySupervisor(
        verify_attestation=lambda **_: True,
        approve_rejoin=lambda **_: True,
        audit=audit_log_sink(audit),
    )
    register(supervisor)
    supervisor.heartbeat(
        node_id="node-a", generation=0, sequence=1, attestation=b"heartbeat"
    )
    supervisor.isolate("node-a", reason="test_isolation")
    events = audit.snapshot()
    assert [entry["event"] for entry in events] == [
        "continuity_node_registered",
        "continuity_node_heartbeat",
        "continuity_node_isolated",
    ]
    assert audit.verify_integrity()
