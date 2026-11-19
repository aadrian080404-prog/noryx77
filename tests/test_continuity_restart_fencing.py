import pytest

from core.continuity import ContinuitySupervisor, NodeContinuityState
from core.sqlite_continuity import SQLiteContinuityStore


def verifier(**claims):
    return claims["attestation"] == (
        claims["node_id"], claims["generation"], claims["sequence"]
    )


def test_active_persisted_node_is_fenced_on_restart_until_fresh_rejoin(tmp_path):
    database = tmp_path / "continuity.sqlite3"
    events = []
    first_store = SQLiteContinuityStore(str(database))
    first = ContinuitySupervisor(
        verify_attestation=verifier,
        approve_rejoin=lambda **_: True,
        audit=lambda event, payload: events.append((event, payload)),
        state_store=first_store,
    )
    first.register(
        node_id="node-a",
        identity_fingerprint="a" * 64,
        capabilities=("compute",),
        attestation=("node-a", 0, 0),
    )
    first.heartbeat(
        node_id="node-a",
        generation=0,
        sequence=7,
        attestation=("node-a", 0, 7),
    )
    assert first.resolve("compute").state is NodeContinuityState.ACTIVE
    first_store.close()

    reopened_store = SQLiteContinuityStore(str(database))
    second = ContinuitySupervisor(
        verify_attestation=verifier,
        approve_rejoin=lambda **_: True,
        audit=lambda event, payload: events.append((event, payload)),
        state_store=reopened_store,
    )
    restored = second.snapshot()[0]
    assert restored.state is NodeContinuityState.ISOLATED
    assert restored.generation == 0
    assert restored.sequence == 7
    assert second.resolve_all("compute") == ()
    assert events[-1][0] == "continuity_node_isolated"
    assert events[-1][1]["reason"] == "restart_revalidation_required"

    rejoined = second.rejoin(
        node_id="node-a",
        generation=1,
        sequence=0,
        attestation=("node-a", 1, 0),
        approval="fresh-approval",
    )
    assert rejoined.state is NodeContinuityState.ACTIVE
    assert rejoined.generation == 1
    assert second.resolve("compute") == rejoined
    reopened_store.close()


def test_restart_fence_persistence_failure_aborts_restore():
    from core.continuity import NodeContinuityRecord

    active = NodeContinuityRecord(
        "node-a", "a" * 64, 0, 3, ("compute",), NodeContinuityState.ACTIVE
    )

    class BrokenStore:
        def load_records(self):
            return (active,)

        def insert_record(self, record):
            raise AssertionError("not used")

        def replace_record(self, previous, replacement):
            return False

    with pytest.raises(RuntimeError, match="continuity_restart_fence_persistence_failed"):
        ContinuitySupervisor(
            verify_attestation=verifier,
            approve_rejoin=lambda **_: True,
            audit=lambda event, payload: None,
            state_store=BrokenStore(),
        )


def test_restart_fence_audit_failure_keeps_persisted_node_isolated(tmp_path):
    database = tmp_path / "continuity.sqlite3"
    store = SQLiteContinuityStore(str(database))
    from core.continuity import NodeContinuityRecord
    store.insert_record(NodeContinuityRecord(
        "node-a", "a" * 64, 2, 9, ("compute",), NodeContinuityState.ACTIVE
    ))
    store.close()

    reopened = SQLiteContinuityStore(str(database))
    with pytest.raises(RuntimeError, match="audit unavailable"):
        ContinuitySupervisor(
            verify_attestation=verifier,
            approve_rejoin=lambda **_: True,
            audit=lambda *_: (_ for _ in ()).throw(RuntimeError("audit unavailable")),
            state_store=reopened,
        )
    persisted = reopened.load_records()[0]
    assert persisted.state is NodeContinuityState.ISOLATED
    reopened.close()
