import hashlib
from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.contracts import TaskSpec
from core.crypto import AuthenticatedCipher, InMemoryKeyProvider
from core.continuity import NodeContinuityState, node_attestation_statement
from core.identity import AgentIdentityAuthority
from core.journal_integrity import InMemoryMonotonicAnchor, JournalAuthenticator
from core.offline import OfflineSnapshot, SQLiteOfflineSyncQueue
from core.offline_adapters import BoundAuthenticatedCipher
from core.offline_snapshot_auth import (
    Ed25519OfflineSnapshotAuthenticator,
    sign_offline_snapshot,
)
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog
from core.sqlite_continuity import SQLiteContinuityStore
from core.sqlite_identity import SQLiteIdentityRegistry


class _OfflineSnapshotAuthenticator:
    def __init__(self, issuer):
        self._authenticator = Ed25519OfflineSnapshotAuthenticator({"runtime-test-issuer": issuer.public_key()})

    def verify(self, snapshot):
        return self._authenticator.verify(snapshot)


class _OfflineAnchor:
    def accept(self, issued_at, snapshot_id):
        return True


def _signed(identity, private_key, generation, sequence):
    fingerprint = hashlib.sha256(identity.public_key).hexdigest()
    statement = node_attestation_statement(
        node_id=identity.agent_id,
        identity_fingerprint=fingerprint,
        generation=generation,
        sequence=sequence,
    )
    return AgentIdentityAuthority.sign(identity, private_key, statement)


def test_full_durable_runtime_recovers_identity_state_offline_queue_ncp_and_audit(tmp_path):
    identity_path = str(tmp_path / "identity.sqlite3")
    state_path = str(tmp_path / "state.sqlite3")
    audit_path = str(tmp_path / "audit.sqlite3")
    continuity_path = str(tmp_path / "continuity.sqlite3")
    offline_path = str(tmp_path / "offline.sqlite3")

    identity_registry = SQLiteIdentityRegistry(identity_path)
    deterministic_identity, _ = AgentIdentityAuthority.generate("deterministic")
    identity_registry.register(deterministic_identity)
    node_identity, node_private_key = AgentIdentityAuthority.generate("persistent-node")
    identity_registry.register(node_identity)
    identity_provider = lambda agent_id: deterministic_identity if agent_id == "deterministic" else None

    state_authenticator = JournalAuthenticator(
        b"runtime-state-journal-key-material-32-bytes!!",
        key_id="runtime-state-key-v1",
    )
    state_anchor = InMemoryMonotonicAnchor()
    audit_anchor = InMemoryMonotonicAnchor()
    audit = SQLiteAuditLog(audit_path)
    continuity_store = SQLiteContinuityStore(continuity_path)

    key_provider = InMemoryKeyProvider({"offline-key": b"o" * 32})
    cipher = AuthenticatedCipher(key_provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    queue = SQLiteOfflineSyncQueue(offline_path, bound_cipher)

    first = NORYXRuntime(
        state_journal_path=state_path,
        state_journal_authenticator=state_authenticator,
        state_journal_anchor=state_anchor,
        audit_log=audit,
        identity_registry=identity_registry,
        agent_identity_provider=identity_provider,
    )
    continuity = first.configure_continuity(
        node_identity_registry=identity_registry,
        approve_rejoin=lambda **_: True,
        continuity_state_store=continuity_store,
    )
    fingerprint = hashlib.sha256(node_identity.public_key).hexdigest()
    continuity.register(
        node_id=node_identity.agent_id,
        identity_fingerprint=fingerprint,
        capabilities=("compute", "storage"),
        attestation=_signed(node_identity, node_private_key, 0, 0),
    )
    continuity.heartbeat(
        node_id=node_identity.agent_id,
        generation=0,
        sequence=7,
        attestation=_signed(node_identity, node_private_key, 0, 7),
    )
    continuity.isolate(node_identity.agent_id, reason="full_restart_test")

    issuer_key = Ed25519PrivateKey.generate()
    first.configure_offline(
        cipher=cipher,
        key_id="offline-key",
        snapshot_authenticator=_OfflineSnapshotAuthenticator(issuer_key),
        clock=lambda: 100,
        offline_queue=queue,
        monotonic_anchor=_OfflineAnchor(),
    )
    unsigned = OfflineSnapshot(
        snapshot_id="runtime-snapshot-1",
        principal_id="principal-1",
        issued_at=100,
        policy_version="policy-1",
        artifact_version="artifact-1",
        capabilities=("local.execute",),
        state_version="state-1",
        principal_key_fingerprint="d" * 64,
        integrity_digest="0" * 64,
    )
    signed_snapshot = sign_offline_snapshot(
        unsigned,
        issuer_key_id="runtime-test-issuer",
        signing_key=issuer_key,
    )
    first.install_offline_snapshot(signed_snapshot)
    task = TaskSpec(
        task_id="offline-task-1",
        task_type="compute",
        objective="durable multi-subsystem restart",
        input={"value": 7},
        execution_id="offline-execution-1",
    )
    result = first.run_offline(
        task,
        capability="local.execute",
        local_executor=lambda _: "verified durable output",
    )
    assert result["status"] == "completed"
    assert result["state_commit"].principal_id == "principal-1"
    assert result["state_commit"].principal_key_fingerprint == "d" * 64
    audit_head = first.checkpoint_audit_anchor(audit_anchor)

    first.state_journal.close()
    audit.close()
    continuity_store.close()
    queue.close()

    reopened_registry = SQLiteIdentityRegistry(identity_path)
    reopened_audit = SQLiteAuditLog(audit_path)
    reopened_continuity_store = SQLiteContinuityStore(continuity_path)
    reopened_queue = SQLiteOfflineSyncQueue(offline_path, bound_cipher)
    second = NORYXRuntime(
        state_journal_path=state_path,
        state_journal_authenticator=state_authenticator,
        state_journal_anchor=state_anchor,
        audit_log=reopened_audit,
        identity_registry=reopened_registry,
        agent_identity_provider=identity_provider,
    )
    restored_continuity = second.configure_continuity(
        node_identity_registry=reopened_registry,
        approve_rejoin=lambda **_: True,
        continuity_state_store=reopened_continuity_store,
    )

    recovered_commit = second.state.get("offline-execution-1")
    assert second.state.version == 1
    assert recovered_commit.principal_id == "principal-1"
    assert recovered_commit.principal_key_fingerprint == "d" * 64
    assert reopened_queue.decrypt("offline-execution-1")
    assert len(reopened_queue) == 1
    assert restored_continuity.snapshot()[0].sequence == 7
    assert restored_continuity.snapshot()[0].state is NodeContinuityState.ISOLATED
    assert reopened_audit.verify_integrity()
    recovered_audit_head = reopened_audit.verify_and_advance_anchor(audit_anchor)
    assert recovered_audit_head.sequence > audit_head.sequence
    assert audit_anchor.read() == recovered_audit_head

    second.state_journal.close()
    reopened_audit.close()
    reopened_continuity_store.close()
    reopened_queue.close()