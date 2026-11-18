"""Fail-closed offline execution, local commit and secure reconnection primitives."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
import sqlite3
import threading
from typing import Callable, Protocol, TypeVar

MAX_ID_BYTES = 256
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_QUEUE_ITEMS = 100_000
MAX_CAPABILITIES = 512
MAX_SNAPSHOT_AGE = 86_400

class OfflineState(str, Enum):
    ONLINE = "online"
    DISCONNECTED = "disconnected"
    READY = "offline_ready"
    EXECUTING = "offline_executing"
    SYNC_PENDING = "sync_pending"
    RECONNECTING = "reconnecting"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    RECOVERY = "recovery"

class RecoveryLike(Protocol):
    def snapshot(self) -> tuple[object, int]: ...
    def run_if_normal(self, operation: Callable[[], object], *, expected_epoch: int | None = None) -> object: ...

class OfflineCipher(Protocol):
    def encrypt(self, plaintext: bytes, *, aad: bytes) -> bytes: ...
    def decrypt(self, ciphertext: bytes, *, aad: bytes) -> bytes: ...

class OfflinePolicy(Protocol):
    def authorize(self, *, principal_id: str, operation: str, offline: bool) -> bool: ...

class OfflineVerifier(Protocol):
    def verify(self, result: object) -> bool: ...

class OfflineSnapshotAuthenticator(Protocol):
    def verify(self, snapshot: "OfflineSnapshot") -> bool: ...

class MonotonicAnchorLike(Protocol):
    def accept(self, issued_at: int, snapshot_id: str) -> bool: ...

class OfflineConflictError(RuntimeError):
    pass

class OfflineDeniedError(RuntimeError):
    pass

def _bounded(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ValueError(f"invalid_{name}")
    return value

def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

@dataclass(frozen=True)
class OfflineSnapshot:
    snapshot_id: str
    principal_id: str
    issued_at: int
    policy_version: str
    artifact_version: str
    capabilities: tuple[str, ...]
    state_version: str
    principal_key_fingerprint: str
    integrity_digest: str
    issuer_key_id: str = ""
    signature: bytes = b""

    def __post_init__(self) -> None:
        for value, name in ((self.snapshot_id, "snapshot_id"), (self.principal_id, "principal_id"),
                            (self.policy_version, "policy_version"), (self.artifact_version, "artifact_version"),
                            (self.state_version, "state_version")):
            _bounded(value, name)
        if isinstance(self.issued_at, bool) or not isinstance(self.issued_at, int) or self.issued_at < 0:
            raise ValueError("invalid_issued_at")
        if not isinstance(self.capabilities, tuple) or not 1 <= len(self.capabilities) <= MAX_CAPABILITIES:
            raise ValueError("invalid_capabilities")
        normalized = tuple(_bounded(cap, "capability") for cap in self.capabilities)
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate_capability")
        if (
            not isinstance(self.principal_key_fingerprint, str)
            or len(self.principal_key_fingerprint) != 64
            or any(c not in "0123456789abcdef" for c in self.principal_key_fingerprint)
        ):
            raise ValueError("invalid_principal_key_fingerprint")
        if not isinstance(self.integrity_digest, str) or len(self.integrity_digest) != 64 or any(c not in "0123456789abcdef" for c in self.integrity_digest):
            raise ValueError("invalid_integrity_digest")
        if not isinstance(self.issuer_key_id, str) or (self.issuer_key_id and (
            not self.issuer_key_id.strip() or len(self.issuer_key_id.encode("utf-8")) > MAX_ID_BYTES
        )):
            raise ValueError("invalid_snapshot_issuer_key_id")
        if not isinstance(self.signature, bytes) or (self.signature and len(self.signature) != 64):
            raise ValueError("invalid_snapshot_signature")

    def canonical_bytes(self) -> bytes:
        body = {"snapshot_id": self.snapshot_id, "principal_id": self.principal_id,
                "issued_at": self.issued_at, "policy_version": self.policy_version,
                "artifact_version": self.artifact_version, "capabilities": self.capabilities,
                "state_version": self.state_version,
                "principal_key_fingerprint": self.principal_key_fingerprint}
        if self.issuer_key_id:
            body["issuer_key_id"] = self.issuer_key_id
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def verify_integrity(self) -> bool:
        return _digest(self.canonical_bytes()) == self.integrity_digest

@dataclass(frozen=True)
class OfflineExecution:
    execution_id: str
    principal_id: str
    operation: str
    capability: str
    payload_digest: str
    base_state_version: str

    def __post_init__(self) -> None:
        for value, name in ((self.execution_id, "execution_id"), (self.principal_id, "principal_id"),
                            (self.operation, "operation"), (self.capability, "capability"),
                            (self.base_state_version, "base_state_version")):
            _bounded(value, name)
        if len(self.payload_digest) != 64 or any(c not in "0123456789abcdef" for c in self.payload_digest):
            raise ValueError("invalid_payload_digest")

def _execution_metadata(execution: OfflineExecution) -> bytes:
    """Canonical metadata authenticated together with the queued payload."""
    return json.dumps({
        "execution_id": execution.execution_id,
        "principal_id": execution.principal_id,
        "operation": execution.operation,
        "capability": execution.capability,
        "payload_digest": execution.payload_digest,
        "base_state_version": execution.base_state_version,
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _execution_aad(execution: OfflineExecution, sequence: int) -> bytes:
    # Bind routing/authority metadata and queue ordering to the payload's AEAD tag.
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
        raise ValueError("invalid_offline_sequence")
    return (
        b"noryx7/offline-sync/v2/"
        + _execution_metadata(execution)
        + b"\\x00"
        + str(sequence).encode("ascii")
    )


@dataclass(frozen=True)
class SyncEnvelope:
    execution: OfflineExecution
    ciphertext: bytes
    record_digest: str
    sequence: int

class OfflineSyncQueue:
    """Bounded encrypted outbox; plaintext is never retained by the queue."""
    def __init__(self, cipher: OfflineCipher, *, max_items: int = MAX_QUEUE_ITEMS) -> None:
        if not isinstance(max_items, int) or isinstance(max_items, bool) or not 1 <= max_items <= MAX_QUEUE_ITEMS:
            raise ValueError("invalid_max_items")
        self._cipher, self._max_items = cipher, max_items
        self._records: dict[str, SyncEnvelope] = {}
        self._sequence = 0
        self._lock = threading.RLock()

    def enqueue(self, execution: OfflineExecution, payload: bytes) -> SyncEnvelope:
        if not isinstance(execution, OfflineExecution):
            raise TypeError("offline_execution_required")
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
            raise ValueError("invalid_payload")
        if _digest(payload) != execution.payload_digest:
            raise OfflineDeniedError("offline_payload_mismatch")
        with self._lock:
            existing = self._records.get(execution.execution_id)
            if existing is not None:
                if existing.execution != execution:
                    raise OfflineConflictError("identity_conflict")
                return existing
            if len(self._records) >= self._max_items:
                raise OfflineDeniedError("offline_sync_queue_full")
            sequence = self._sequence + 1
            ciphertext = self._cipher.encrypt(
                payload, aad=_execution_aad(execution, sequence)
            )
            if not isinstance(ciphertext, bytes) or not ciphertext or ciphertext == payload:
                raise OfflineDeniedError("encryption_required")
            self._sequence = sequence
            envelope = SyncEnvelope(execution, ciphertext, _digest(ciphertext), sequence)
            self._records[execution.execution_id] = envelope
            return envelope

    def decrypt(self, execution_id: str) -> bytes:
        _bounded(execution_id, "execution_id")
        with self._lock:
            envelope = self._records[execution_id]
            if _digest(envelope.ciphertext) != envelope.record_digest:
                raise OfflineDeniedError("offline_record_integrity_failed")
            plaintext = self._cipher.decrypt(
                envelope.ciphertext, aad=_execution_aad(envelope.execution, envelope.sequence)
            )
            if not isinstance(plaintext, bytes) or not plaintext or _digest(plaintext) != envelope.execution.payload_digest:
                raise OfflineDeniedError("offline_payload_integrity_failed")
            return plaintext

    def acknowledge(self, execution_id: str) -> None:
        with self._lock:
            self._records.pop(_bounded(execution_id, "execution_id"), None)

    def snapshot(self) -> tuple[SyncEnvelope, ...]:
        with self._lock:
            return tuple(self._records.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)


class SQLiteOfflineSyncQueue:
    """Crash-persistent encrypted outbox backed by SQLite.

    The cipher and its key lifecycle are supplied by the caller. SQLite stores
    ciphertext plus canonical execution metadata only. This is local durable
    storage, not distributed consensus or a cross-device replication protocol.
    """

    def __init__(self, database_path: str, cipher: OfflineCipher, *,
                 max_items: int = MAX_QUEUE_ITEMS, busy_timeout_ms: int = 5000) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("offline_database_path_required")
        if database_path == ":memory:":
            raise ValueError("persistent_offline_database_required")
        if not callable(getattr(cipher, "encrypt", None)) or not callable(getattr(cipher, "decrypt", None)):
            raise TypeError("offline_cipher_contract_required")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= MAX_QUEUE_ITEMS:
            raise ValueError("invalid_max_items")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or not 1 <= busy_timeout_ms <= 60000:
            raise ValueError("invalid_busy_timeout")
        self._cipher, self._max_items = cipher, max_items
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            database_path, timeout=busy_timeout_ms / 1000,
            isolation_level=None, check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS offline_sync_queue (
                execution_id TEXT PRIMARY KEY,
                execution_json TEXT NOT NULL,
                ciphertext BLOB NOT NULL,
                record_digest TEXT NOT NULL,
                sequence INTEGER NOT NULL UNIQUE CHECK(sequence > 0)
            )
        """)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS offline_sync_meta (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL CHECK(value >= 0)
            )
        """)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            for key, value in (
                ("sequence", 0),
                ("schema_version", 1),
                ("max_items", max_items),
            ):
                self._connection.execute(
                    "INSERT OR IGNORE INTO offline_sync_meta(key, value) VALUES (?, ?)",
                    (key, value),
                )
            stored_config = {
                row["key"]: row["value"]
                for row in self._connection.execute(
                    "SELECT key, value FROM offline_sync_meta "
                    "WHERE key IN ('schema_version', 'max_items')"
                ).fetchall()
            }
            if stored_config != {"schema_version": 1, "max_items": max_items}:
                raise ValueError("offline_queue_configuration_mismatch")
            self._connection.execute("COMMIT")
        except Exception:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            self._connection.close()
            raise
        try:
            os.chmod(database_path, 0o600)
        except OSError as exc:
            self._connection.close()
            raise OfflineDeniedError("offline_database_permissions_unavailable") from exc

    @staticmethod
    def _execution_json(execution: OfflineExecution) -> str:
        return _execution_metadata(execution).decode("utf-8")

    @staticmethod
    def _decode_execution(value: str) -> OfflineExecution:
        try:
            payload = json.loads(value)
            if not isinstance(payload, dict) or set(payload) != {
                "execution_id", "principal_id", "operation", "capability",
                "payload_digest", "base_state_version",
            }:
                raise ValueError("offline_execution_metadata_invalid")
            return OfflineExecution(**payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OfflineDeniedError("offline_execution_metadata_invalid") from exc

    @classmethod
    def _row_to_envelope(cls, row: sqlite3.Row) -> SyncEnvelope:
        execution = cls._decode_execution(row["execution_json"])
        ciphertext = bytes(row["ciphertext"])
        digest = row["record_digest"]
        sequence = row["sequence"]
        if (
            not ciphertext or not isinstance(digest, str)
            or digest != _digest(ciphertext)
            or isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0
            or execution.execution_id != row["execution_id"]
        ):
            raise OfflineDeniedError("offline_record_integrity_failed")
        return SyncEnvelope(execution, ciphertext, digest, sequence)

    def enqueue(self, execution: OfflineExecution, payload: bytes) -> SyncEnvelope:
        if not isinstance(execution, OfflineExecution):
            raise TypeError("offline_execution_required")
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
            raise ValueError("invalid_payload")
        if _digest(payload) != execution.payload_digest:
            raise OfflineDeniedError("offline_payload_mismatch")
        encoded_execution = self._execution_json(execution)
        with self._lock:
            connection = self._connection
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT * FROM offline_sync_queue WHERE execution_id=?",
                    (execution.execution_id,),
                ).fetchone()
                if existing is not None:
                    envelope = self._row_to_envelope(existing)
                    if envelope.execution != execution:
                        raise OfflineConflictError("identity_conflict")
                    self._decrypt_envelope(envelope)
                    connection.execute("COMMIT")
                    return envelope
                count = connection.execute(
                    "SELECT COUNT(*) FROM offline_sync_queue"
                ).fetchone()[0]
                if count >= self._max_items:
                    raise OfflineDeniedError("offline_sync_queue_full")
                sequence = connection.execute(
                    "SELECT value FROM offline_sync_meta WHERE key='sequence'"
                ).fetchone()[0] + 1
                ciphertext = self._cipher.encrypt(
                    payload, aad=_execution_aad(execution, sequence)
                )
                if not isinstance(ciphertext, bytes) or not ciphertext or ciphertext == payload:
                    raise OfflineDeniedError("encryption_required")
                digest = _digest(ciphertext)
                connection.execute(
                    "UPDATE offline_sync_meta SET value=? WHERE key='sequence'",
                    (sequence,),
                )
                connection.execute(
                    "INSERT INTO offline_sync_queue "
                    "(execution_id, execution_json, ciphertext, record_digest, sequence) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (execution.execution_id, encoded_execution, ciphertext, digest, sequence),
                )
                connection.execute("COMMIT")
                return SyncEnvelope(execution, ciphertext, digest, sequence)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _decrypt_envelope(self, envelope: SyncEnvelope) -> bytes:
        try:
            plaintext = self._cipher.decrypt(
                envelope.ciphertext, aad=_execution_aad(envelope.execution, envelope.sequence)
            )
        except Exception as exc:
            raise OfflineDeniedError(
                "offline_execution_metadata_authentication_failed"
            ) from exc
        if (
            not isinstance(plaintext, bytes) or not plaintext
            or _digest(plaintext) != envelope.execution.payload_digest
        ):
            raise OfflineDeniedError("offline_payload_integrity_failed")
        return plaintext

    def decrypt(self, execution_id: str) -> bytes:
        _bounded(execution_id, "execution_id")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM offline_sync_queue WHERE execution_id=?",
                (execution_id,),
            ).fetchone()
            if row is None:
                raise KeyError(execution_id)
            envelope = self._row_to_envelope(row)
            return self._decrypt_envelope(envelope)

    def acknowledge(self, execution_id: str) -> None:
        _bounded(execution_id, "execution_id")
        with self._lock:
            self._connection.execute(
                "DELETE FROM offline_sync_queue WHERE execution_id=?",
                (execution_id,),
            )

    def snapshot(self) -> tuple[SyncEnvelope, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM offline_sync_queue ORDER BY sequence"
            ).fetchall()
            envelopes = tuple(self._row_to_envelope(row) for row in rows)
            # Authenticate metadata before callers use it for routing or sync.
            # Each payload is checked and discarded one at a time to bound memory.
            for envelope in envelopes:
                self._decrypt_envelope(envelope)
            return envelopes

    def __len__(self) -> int:
        with self._lock:
            return self._connection.execute(
                "SELECT COUNT(*) FROM offline_sync_queue"
            ).fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


T = TypeVar("T")

class OfflineRuntime:
    """Offline admission -> durable monotonic admission -> encrypted outbox -> verified commit -> sync."""
    def __init__(self, *, recovery: RecoveryLike, policy: OfflinePolicy, verifier: OfflineVerifier,
                 cipher: OfflineCipher, clock: Callable[[], int],
                 snapshot_authenticator: OfflineSnapshotAuthenticator,
                 max_snapshot_age: int = MAX_SNAPSHOT_AGE,
                 monotonic_anchor: MonotonicAnchorLike | None = None,
                 queue: OfflineSyncQueue | SQLiteOfflineSyncQueue | None = None) -> None:
        if not callable(getattr(snapshot_authenticator, "verify", None)) or not callable(clock):
            raise TypeError("offline_snapshot_authenticator_and_clock_required")
        if isinstance(max_snapshot_age, bool) or not isinstance(max_snapshot_age, int) or max_snapshot_age < 0:
            raise ValueError("invalid_max_snapshot_age")
        self._recovery, self._policy, self._verifier = recovery, policy, verifier
        self._clock, self._snapshot_authenticator = clock, snapshot_authenticator
        if queue is not None and not all(callable(getattr(queue, name, None)) for name in ("enqueue", "decrypt", "acknowledge", "snapshot")):
            raise TypeError("offline_queue_contract_required")
        self._queue = queue if queue is not None else OfflineSyncQueue(cipher)
        self._snapshot: OfflineSnapshot | None = None
        self._state = OfflineState.ONLINE
        self._lock = threading.RLock()
        self._max_snapshot_age = max_snapshot_age
        self._monotonic_anchor = monotonic_anchor
        self._highest_snapshot_issued_at: int | None = None
        self._highest_snapshot_id: str | None = None

    def _authenticated_snapshot(self, snapshot: OfflineSnapshot) -> bool:
        if not isinstance(snapshot, OfflineSnapshot) or not snapshot.verify_integrity():
            return False
        try:
            return self._snapshot_authenticator.verify(snapshot) is True
        except Exception:
            return False

    @property
    def state(self) -> OfflineState:
        with self._lock:
            return self._state

    @property
    def queue(self) -> OfflineSyncQueue | SQLiteOfflineSyncQueue:
        return self._queue

    def install_snapshot(self, snapshot: OfflineSnapshot) -> None:
        if not self._authenticated_snapshot(snapshot):
            raise OfflineDeniedError("invalid_offline_snapshot")
        now = self._clock()
        if snapshot.issued_at > now or now - snapshot.issued_at > self._max_snapshot_age:
            raise OfflineDeniedError("stale_offline_snapshot")
        if self._monotonic_anchor is not None:
            try:
                anchored = self._monotonic_anchor.accept(snapshot.issued_at, snapshot.snapshot_id)
            except Exception as exc:
                raise OfflineDeniedError("offline_anchor_unavailable") from exc
            if anchored is not True:
                raise OfflineDeniedError("offline_snapshot_rollback")
        with self._lock:
            if self._highest_snapshot_issued_at is not None:
                if snapshot.issued_at < self._highest_snapshot_issued_at:
                    raise OfflineDeniedError("offline_snapshot_rollback")
                if snapshot.issued_at == self._highest_snapshot_issued_at and snapshot.snapshot_id != self._highest_snapshot_id:
                    raise OfflineDeniedError("offline_snapshot_same_epoch_conflict")
            self._snapshot = snapshot
            self._highest_snapshot_issued_at = snapshot.issued_at
            self._highest_snapshot_id = snapshot.snapshot_id
            self._state = OfflineState.READY

    def disconnect(self) -> None:
        with self._lock:
            self._state = OfflineState.READY if self._snapshot is not None else OfflineState.DISCONNECTED

    def _admit(self, execution: OfflineExecution, payload: bytes) -> int:
        with self._lock:
            snapshot = self._snapshot
            if snapshot is None or not self._authenticated_snapshot(snapshot):
                raise OfflineDeniedError("offline_snapshot_required")
            now = self._clock()
            if snapshot.issued_at > now or now - snapshot.issued_at > self._max_snapshot_age:
                self._state = OfflineState.RECOVERY
                raise OfflineDeniedError("stale_offline_snapshot")
            if snapshot.principal_id != execution.principal_id:
                raise OfflineDeniedError("offline_identity_mismatch")
            if execution.capability not in snapshot.capabilities:
                raise OfflineDeniedError("offline_capability_denied")
            if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
                raise ValueError("invalid_payload")
            if _digest(payload) != execution.payload_digest:
                raise OfflineDeniedError("offline_payload_mismatch")
            try:
                policy_allowed = self._policy.authorize(principal_id=execution.principal_id, operation=execution.operation, offline=True)
            except Exception:
                policy_allowed = False
            if policy_allowed is not True:
                raise OfflineDeniedError("offline_policy_denied")
            recovery_state, epoch = self._recovery.snapshot()
            if str(getattr(recovery_state, "value", recovery_state)).lower() != "normal":
                self._state = OfflineState.RECOVERY
                raise OfflineDeniedError("offline_recovery_denied")
            self._state = OfflineState.EXECUTING
            return epoch

    def execute(self, *, execution: OfflineExecution, payload: bytes, result: T | None = None,
                execute: Callable[[], T] | None = None, commit: Callable[[OfflineExecution, T], None]) -> SyncEnvelope:
        if (result is None) == (execute is None):
            raise ValueError("provide_exactly_one_result_source")
        epoch = self._admit(execution, payload)
        envelope = None
        try:
            envelope = self._queue.enqueue(execution, payload)
            def critical() -> None:
                produced = execute() if execute is not None else result
                try:
                    verified = self._verifier.verify(produced)
                except Exception:
                    verified = False
                if verified is not True:
                    raise OfflineDeniedError("offline_result_unverified")
                commit(execution, produced)  # type: ignore[arg-type]
            self._recovery.run_if_normal(critical, expected_epoch=epoch)
        except Exception:
            if envelope is not None:
                self._queue.acknowledge(execution.execution_id)
            with self._lock:
                self._state = OfflineState.RECOVERY
            raise
        with self._lock:
            self._state = OfflineState.SYNC_PENDING
        return envelope

    def reconnect(self, *, authenticated: bool, channel_verified: bool) -> tuple[SyncEnvelope, ...]:
        if authenticated is not True or channel_verified is not True:
            raise OfflineDeniedError("secure_reconnect_required")
        with self._lock:
            if self._snapshot is None or not self._authenticated_snapshot(self._snapshot):
                raise OfflineDeniedError("offline_snapshot_required")
            self._state = OfflineState.SYNCING
            return self._queue.snapshot()

    def acknowledge_synced(self, execution_id: str, *, remote_state_version: str | None = None,
                           conflict: bool = False) -> None:
        with self._lock:
            if conflict:
                self._state = OfflineState.CONFLICT
                raise OfflineConflictError("offline_sync_conflict")
            _bounded(execution_id, "execution_id")
            matching = next((item for item in self._queue.snapshot() if item.execution.execution_id == execution_id), None)
            if matching is None:
                raise KeyError(execution_id)
            if remote_state_version is not None and remote_state_version != matching.execution.base_state_version:
                self._state = OfflineState.CONFLICT
                raise OfflineConflictError("offline_state_version_conflict")
            self._queue.acknowledge(execution_id)
            self._state = OfflineState.SYNC_PENDING if len(self._queue) else OfflineState.ONLINE