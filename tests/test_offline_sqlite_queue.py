from hashlib import sha256
import json
import sqlite3

import pytest

from core.offline import (
    OfflineConflictError,
    OfflineDeniedError,
    OfflineExecution,
    SQLiteOfflineSyncQueue,
)


class Cipher:
    """Deterministic opaque test double; not a production cryptographic cipher."""

    def encrypt(self, plaintext, *, aad):
        prefix = b"TEST:" + sha256(aad).digest()
        return prefix + bytes(value ^ 0xA5 for value in plaintext)

    def decrypt(self, ciphertext, *, aad):
        prefix = b"TEST:" + sha256(aad).digest()
        if not ciphertext.startswith(prefix):
            raise ValueError("bad_ciphertext")
        return bytes(value ^ 0xA5 for value in ciphertext[len(prefix):])


def execution(payload=b"persist me", execution_id="exec-1"):
    return OfflineExecution(
        execution_id=execution_id,
        principal_id="principal-1",
        operation="local-op",
        capability="local.execute",
        payload_digest=sha256(payload).hexdigest(),
        base_state_version="state-1",
    )


def test_sqlite_outbox_survives_close_and_reopen(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    payload = b"persist me"
    first = SQLiteOfflineSyncQueue(path, Cipher())
    envelope = first.enqueue(execution(payload), payload)
    first.close()

    reopened = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        assert len(reopened) == 1
        assert reopened.snapshot() == (envelope,)
        assert reopened.decrypt("exec-1") == payload
    finally:
        reopened.close()


def test_sqlite_outbox_stores_ciphertext_not_plaintext(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    payload = b"highly private offline payload"
    queue = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        queue.enqueue(execution(payload), payload)
        connection = sqlite3.connect(path)
        try:
            stored = connection.execute(
                "SELECT execution_json, ciphertext FROM offline_sync_queue"
            ).fetchone()
        finally:
            connection.close()
        assert payload not in stored[0].encode("utf-8")
        assert payload not in stored[1]
        assert b"principal-1" in stored[0].encode("utf-8")
    finally:
        queue.close()


def test_sqlite_outbox_duplicate_is_idempotent_across_reopen(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    payload = b"same operation"
    first = SQLiteOfflineSyncQueue(path, Cipher())
    original = first.enqueue(execution(payload), payload)
    first.close()

    second = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        duplicate = second.enqueue(execution(payload), payload)
        assert duplicate == original
        assert len(second) == 1
    finally:
        second.close()


def test_sqlite_outbox_rejects_execution_identity_reuse(tmp_path):
    queue = SQLiteOfflineSyncQueue(str(tmp_path / "offline.sqlite"), Cipher())
    try:
        payload = b"first"
        queue.enqueue(execution(payload), payload)
        changed = execution(b"second")
        with pytest.raises(OfflineConflictError, match="identity_conflict"):
            queue.enqueue(changed, b"second")
    finally:
        queue.close()


def test_sqlite_outbox_sequence_survives_acknowledgement_and_restart(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    first = SQLiteOfflineSyncQueue(path, Cipher())
    one = b"one"
    first_envelope = first.enqueue(execution(one, "exec-1"), one)
    first.acknowledge("exec-1")
    first.close()

    second = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        two = b"two"
        second_envelope = second.enqueue(execution(two, "exec-2"), two)
        assert second_envelope.sequence == first_envelope.sequence + 1
    finally:
        second.close()


def test_sqlite_outbox_enforces_capacity_atomically(tmp_path):
    queue = SQLiteOfflineSyncQueue(
        str(tmp_path / "offline.sqlite"), Cipher(), max_items=1
    )
    try:
        one = b"one"
        queue.enqueue(execution(one, "exec-1"), one)
        two = b"two"
        with pytest.raises(OfflineDeniedError, match="queue_full"):
            queue.enqueue(execution(two, "exec-2"), two)
        assert len(queue) == 1
    finally:
        queue.close()


def test_sqlite_outbox_detects_ciphertext_tampering(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    queue = SQLiteOfflineSyncQueue(path, Cipher())
    payload = b"tamper probe"
    queue.enqueue(execution(payload), payload)
    queue.close()

    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE offline_sync_queue SET ciphertext=? WHERE execution_id=?",
            (b"tampered", "exec-1"),
        )
        connection.commit()
    finally:
        connection.close()

    reopened = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        with pytest.raises(OfflineDeniedError, match="integrity"):
            reopened.snapshot()
    finally:
        reopened.close()


def test_sqlite_outbox_rejects_invalid_configuration(tmp_path):
    with pytest.raises(ValueError, match="max_items"):
        SQLiteOfflineSyncQueue(str(tmp_path / "bad.sqlite"), Cipher(), max_items=True)
    with pytest.raises(ValueError, match="busy_timeout"):
        SQLiteOfflineSyncQueue(str(tmp_path / "bad-timeout.sqlite"), Cipher(), busy_timeout_ms=0)

def test_sqlite_outbox_detects_execution_metadata_tampering(tmp_path):
    path = str(tmp_path / "offline.sqlite")
    payload = b"metadata binding probe"
    queue = SQLiteOfflineSyncQueue(path, Cipher())
    queue.enqueue(execution(payload), payload)
    queue.close()

    connection = sqlite3.connect(path)
    try:
        row = connection.execute(
            "SELECT execution_json FROM offline_sync_queue WHERE execution_id=?",
            ("exec-1",),
        ).fetchone()
        metadata = json.loads(row[0])
        metadata["principal_id"] = "attacker-principal"
        connection.execute(
            "UPDATE offline_sync_queue SET execution_json=? WHERE execution_id=?",
            (json.dumps(metadata, sort_keys=True, separators=(",", ":")), "exec-1"),
        )
        connection.commit()
    finally:
        connection.close()

    reopened = SQLiteOfflineSyncQueue(path, Cipher())
    try:
        with pytest.raises(OfflineDeniedError, match="metadata_authentication"):
            reopened.snapshot()
    finally:
        reopened.close()
