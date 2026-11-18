import hashlib
import os
import stat

import pytest

from core.continuity import NodeContinuityState, node_attestation_statement
from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime
from core.sqlite_continuity import SQLiteContinuityStore
from core.sqlite_identity import SQLiteIdentityRegistry


def _signed(identity, private_key, generation, sequence):
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    statement = node_attestation_statement(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        generation=generation,
        sequence=sequence,
    )
    return AgentIdentityAuthority.sign(identity, private_key, statement)


def test_ncp_state_survives_runtime_restart(tmp_path):
    identity_path = str(tmp_path / "identity.sqlite3")
    continuity_path = str(tmp_path / "continuity.sqlite3")
    identity_registry = SQLiteIdentityRegistry(identity_path)
    identity, private_key = AgentIdentityAuthority.generate("persistent-node")
    identity_registry.register(identity)

    first_store = SQLiteContinuityStore(continuity_path)
    first_runtime = NORYXRuntime()
    first = first_runtime.configure_continuity(
        node_identity_registry=identity_registry,
        approve_rejoin=lambda **_: True,
        continuity_state_store=first_store,
    )
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    first.register(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        capabilities=("compute", "storage"),
        attestation=_signed(identity, private_key, 0, 0),
    )
    first.heartbeat(
        node_id=identity.agent_id,
        generation=0,
        sequence=7,
        attestation=_signed(identity, private_key, 0, 7),
    )
    first.isolate(identity.agent_id, reason="restart_recovery_test")
    first_store.close()

    reopened_identity_registry = SQLiteIdentityRegistry(identity_path)
    second_store = SQLiteContinuityStore(continuity_path)
    second_runtime = NORYXRuntime()
    second = second_runtime.configure_continuity(
        node_identity_registry=reopened_identity_registry,
        approve_rejoin=lambda **_: True,
        continuity_state_store=second_store,
    )

    restored = second.snapshot()
    assert len(restored) == 1
    assert restored[0].node_id == identity.agent_id
    assert restored[0].generation == 0
    assert restored[0].sequence == 7
    assert restored[0].state is NodeContinuityState.ISOLATED
    assert second.resolve_all("compute") == ()
    second_store.close()


def test_ncp_persisted_heartbeat_advances_sequence_across_restart(tmp_path):
    path = str(tmp_path / "continuity.sqlite3")
    first = SQLiteContinuityStore(path)
    from core.continuity import NodeContinuityRecord
    record = NodeContinuityRecord(
        "node-a", "a" * 64, 2, 9, ("compute",), NodeContinuityState.ACTIVE
    )
    first.insert_record(record)
    first.close()

    second = SQLiteContinuityStore(path)
    restored = second.load_records()
    assert restored == (record,)
    with pytest.raises(Exception):
        second.insert_record(record)
    second.close()


def test_ncp_store_compare_and_swap_rejects_stale_state(tmp_path):
    from core.continuity import NodeContinuityRecord
    store = SQLiteContinuityStore(str(tmp_path / "cas.sqlite3"))
    old = NodeContinuityRecord(
        "node-b", "b" * 64, 0, 0, ("compute",), NodeContinuityState.ACTIVE
    )
    new = NodeContinuityRecord(
        "node-b", "b" * 64, 0, 1, ("compute",), NodeContinuityState.ACTIVE
    )
    store.insert_record(old)
    assert store.replace_record(old, new) is True
    assert store.replace_record(old, old) is False
    assert store.load_records() == (new,)
    store.close()


def test_ncp_store_rejects_in_memory_database():
    with pytest.raises(ValueError, match="persistent_continuity_database_required"):
        SQLiteContinuityStore(":memory:")


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permission semantics required")
def test_ncp_store_restricts_database_permissions(tmp_path):
    path = tmp_path / "private-continuity.sqlite3"
    store = SQLiteContinuityStore(str(path))
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        store.close()


def test_ncp_isolation_is_durable_even_if_audit_sink_fails(tmp_path):
    from core.continuity import ContinuitySupervisor

    should_fail = {"value": False}

    def audit(event, payload):
        if should_fail["value"] and event == "continuity_node_isolated":
            raise OSError("audit sink unavailable")

    path = str(tmp_path / "audit-failure-continuity.sqlite3")
    store = SQLiteContinuityStore(path)
    supervisor = ContinuitySupervisor(
        verify_attestation=lambda **_: True,
        approve_rejoin=lambda **_: True,
        audit=audit,
        state_store=store,
    )
    supervisor.register(
        node_id="audit-failure-node",
        identity_fingerprint="c" * 64,
        capabilities=("compute",),
        attestation=object(),
    )
    should_fail["value"] = True
    with pytest.raises(OSError, match="audit sink unavailable"):
        supervisor.isolate("audit-failure-node", reason="audit_failure_test")
    store.close()

    reopened = SQLiteContinuityStore(path)
    assert reopened.load_records()[0].state is NodeContinuityState.ISOLATED
    reopened.close()
