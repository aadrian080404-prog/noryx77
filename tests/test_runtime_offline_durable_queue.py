import hashlib

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
