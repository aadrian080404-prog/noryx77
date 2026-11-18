import hashlib
import sqlite3

from core.crypto import AuthenticatedCipher, InMemoryKeyProvider
from core.offline import OfflineExecution, SQLiteOfflineSyncQueue
from core.offline_adapters import BoundAuthenticatedCipher
from core.runtime import NORYXRuntime


class _Anchor:
    def accept(self, issued_at, snapshot_id):
        return True


def test_runtime_uses_injected_sqlite_offline_outbox(tmp_path):
    provider = InMemoryKeyProvider({"offline-key": b"k" * 32})
    cipher = AuthenticatedCipher(provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    path = str(tmp_path / "runtime-offline.sqlite3")
    queue = SQLiteOfflineSyncQueue(path, bound_cipher)

    runtime = NORYXRuntime()
    runtime.configure_offline(
        cipher=cipher,
        key_id="offline-key",
        snapshot_authenticator=lambda snapshot: True,
        clock=lambda: 100,
        offline_queue=queue,
        monotonic_anchor=_Anchor(),
    )

    assert runtime.offline is not None
    assert runtime.offline.queue is queue
    assert runtime.offline._monotonic_anchor is not None
    queue.close()


def test_runtime_offline_outbox_payload_survives_queue_reopen(tmp_path):
    provider = InMemoryKeyProvider({"offline-key": b"z" * 32})
    cipher = AuthenticatedCipher(provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    path = str(tmp_path / "persistent-outbox.sqlite3")
    payload = b"verified offline operation"
    execution = OfflineExecution(
        execution_id="offline-execution-1",
        principal_id="principal-1",
        operation="local-analysis",
        capability="analysis",
        payload_digest=hashlib.sha256(payload).hexdigest(),
        base_state_version="state-4",
    )

    first = SQLiteOfflineSyncQueue(path, bound_cipher)
    envelope = first.enqueue(execution, payload)
    first.close()

    reopened = SQLiteOfflineSyncQueue(path, bound_cipher)
    assert len(reopened) == 1
    assert reopened.snapshot()[0] == envelope
    assert reopened.decrypt(execution.execution_id) == payload
    reopened.close()


def test_runtime_offline_outbox_rejects_execution_id_rebinding_after_restart(tmp_path):
    from core.offline import OfflineConflictError

    provider = InMemoryKeyProvider({"offline-key": b"q" * 32})
    cipher = AuthenticatedCipher(provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    path = str(tmp_path / "rebind-outbox.sqlite3")
    original_payload = b"approved operation"
    original = OfflineExecution(
        execution_id="stable-execution-id",
        principal_id="principal-1",
        operation="local-analysis",
        capability="analysis",
        payload_digest=hashlib.sha256(original_payload).hexdigest(),
        base_state_version="state-1",
    )
    first = SQLiteOfflineSyncQueue(path, bound_cipher)
    first.enqueue(original, original_payload)
    first.close()

    reopened = SQLiteOfflineSyncQueue(path, bound_cipher)
    rebound_payload = b"different operation"
    rebound = OfflineExecution(
        execution_id="stable-execution-id",
        principal_id="principal-2",
        operation="privileged-operation",
        capability="admin",
        payload_digest=hashlib.sha256(rebound_payload).hexdigest(),
        base_state_version="state-1",
    )
    try:
        reopened.enqueue(rebound, rebound_payload)
    except OfflineConflictError as exc:
        assert str(exc) == "identity_conflict"
    else:
        raise AssertionError("execution ID rebinding was accepted")
    reopened.close()


def test_runtime_offline_outbox_detects_ciphertext_tampering(tmp_path):
    import pytest
    from core.offline import OfflineDeniedError

    provider = InMemoryKeyProvider({"offline-key": b"t" * 32})
    cipher = AuthenticatedCipher(provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    path = str(tmp_path / "tampered-outbox.sqlite3")
    payload = b"payload-that-must-remain-authenticated"
    execution = OfflineExecution(
        execution_id="tamper-detect-1",
        principal_id="principal-1",
        operation="local-analysis",
        capability="analysis",
        payload_digest=hashlib.sha256(payload).hexdigest(),
        base_state_version="state-1",
    )
    queue = SQLiteOfflineSyncQueue(path, bound_cipher)
    queue.enqueue(execution, payload)
    queue.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE offline_sync_queue SET ciphertext=? WHERE execution_id=?",
        (b"tampered-ciphertext", execution.execution_id),
    )
    connection.commit()
    connection.close()

    reopened = SQLiteOfflineSyncQueue(path, bound_cipher)
    with pytest.raises(OfflineDeniedError, match="offline_record_integrity_failed"):
        reopened.snapshot()
    reopened.close()


def test_runtime_run_offline_uses_authenticated_snapshot_principal(tmp_path):
    from dataclasses import replace

    from core.contracts import TaskSpec
    from core.offline import OfflineSnapshot

    provider = InMemoryKeyProvider({"offline-key": b"r" * 32})
    cipher = AuthenticatedCipher(provider)
    bound_cipher = BoundAuthenticatedCipher(cipher, key_id="offline-key")
    queue = SQLiteOfflineSyncQueue(str(tmp_path / "runtime-execution.sqlite3"), bound_cipher)
    runtime = NORYXRuntime()
    runtime.configure_offline(
        cipher=cipher,
        key_id="offline-key",
        snapshot_authenticator=lambda snapshot: True,
        clock=lambda: 100,
        offline_queue=queue,
        monotonic_anchor=_Anchor(),
    )

    unsigned = OfflineSnapshot(
        snapshot_id="runtime-snapshot-1",
        principal_id="principal-1",
        issued_at=100,
        policy_version="policy-1",
        artifact_version="artifact-1",
        capabilities=("local.execute",),
        state_version="state-1",
        principal_key_fingerprint="c" * 64,
        integrity_digest="0" * 64,
    )
    snapshot = replace(
        unsigned,
        integrity_digest=hashlib.sha256(unsigned.canonical_bytes()).hexdigest(),
    )
    runtime.install_offline_snapshot(snapshot)

    task = TaskSpec(
        task_id="offline-task-1",
        task_type="compute",
        objective="verify offline principal binding",
        input={"value": 7},
        execution_id="offline-execution-1",
    )
    result = runtime.run_offline(
        task,
        capability="local.execute",
        local_executor=lambda _: "verified offline result",
    )

    assert result["status"] == "completed"
    assert result["execution_id"] == "offline-execution-1"
    assert result["state_commit"].principal_id == "principal-1"
    assert result["state_commit"].principal_key_fingerprint == "c" * 64
    assert len(queue) == 1
    assert queue.decrypt("offline-execution-1")
    queue.close()
