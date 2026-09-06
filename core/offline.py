"""Fail-closed offline execution and reconnection primitives for NORYX7.

Offline mode is a constrained execution mode, not a security bypass.  It requires
an authenticated local snapshot, approved local capabilities, the same recovery
state and policy gates used online, and verified results before local commit.
Synchronization is encrypted, bounded, idempotent, and conflict-detecting.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import threading
from typing import Callable, Mapping, Protocol


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
    def require_normal(self, expected_epoch: int | None = None) -> None: ...


class OfflineCipher(Protocol):
    """Authenticated encryption adapter; implementations must never return plaintext."""

    def encrypt(self, plaintext: bytes, *, aad: bytes) -> bytes: ...
    def decrypt(self, ciphertext: bytes, *, aad: bytes) -> bytes: ...


class OfflinePolicy(Protocol):
    def authorize(self, *, principal_id: str, operation: str, offline: bool) -> bool: ...


class OfflineVerifier(Protocol):
    def verify(self, result: object) -> bool: ...


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
    integrity_digest: str

    def __post_init__(self) -> None:
        _bounded(self.snapshot_id, "snapshot_id")
        _bounded(self.principal_id, "principal_id")
        _bounded(self.policy_version, "policy_version")
        _bounded(self.artifact_version, "artifact_version")
        _bounded(self.state_version, "state_version")
        if isinstance(self.issued_at, bool) or not isinstance(self.issued_at, int) or self.issued_at < 0:
            raise ValueError("invalid_issued_at")
        if not 1 <= len(self.capabilities) <= MAX_CAPABILITIES:
            raise ValueError("invalid_capabilities")
        normalized = tuple(_bounded(cap, "capability") for cap in self.capabilities)
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate_capability")
        if not isinstance(self.integrity_digest, str) or len(self.integrity_digest) != 64:
            raise ValueError("invalid_integrity_digest")
        if any(c not in "0123456789abcdef" for c in self.integrity_digest):
            raise ValueError("invalid_integrity_digest")

    def canonical_bytes(self) -> bytes:
        body = {
            "snapshot_id": self.snapshot_id,
            "principal_id": self.principal_id,
            "issued_at": self.issued_at,
            "policy_version": self.policy_version,
            "artifact_version": self.artifact_version,
            "capabilities": self.capabilities,
            "state_version": self.state_version,
        }
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
        for value, name in (
            (self.execution_id, "execution_id"),
            (self.principal_id, "principal_id"),
            (self.operation, "operation"),
            (self.capability, "capability"),
            (self.base_state_version, "base_state_version"),
        ):
            _bounded(value, name)
        if len(self.payload_digest) != 64 or any(c not in "0123456789abcdef" for c in self.payload_digest):
            raise ValueError("invalid_payload_digest")


@dataclass(frozen=True)
class SyncEnvelope:
    execution: OfflineExecution
    ciphertext: bytes
    record_digest: str
    sequence: int


class OfflineSyncQueue:
    """Encrypted local outbox with bounded storage and idempotent execution IDs."""

    def __init__(self, cipher: OfflineCipher, *, max_items: int = MAX_QUEUE_ITEMS) -> None:
        if not isinstance(max_items, int) or isinstance(max_items, bool) or not 1 <= max_items <= MAX_QUEUE_ITEMS:
            raise ValueError("invalid_max_items")
        self._cipher = cipher
        self._max_items = max_items
        self._records: dict[str, SyncEnvelope] = {}
        self._sequence = 0
        self._lock = threading.RLock()

    def enqueue(self, execution: OfflineExecution, payload: bytes) -> SyncEnvelope:
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
            raise ValueError("invalid_payload")
        with self._lock:
            existing = self._records.get(execution.execution_id)
            if existing is not None:
                return existing
            if len(self._records) >= self._max_items:
                raise OfflineDeniedError("offline_sync_queue_full")
            aad = f"noryx7/offline-sync/v1/{execution.execution_id}".encode("utf-8")
            ciphertext = self._cipher.encrypt(payload, aad=aad)
            if not isinstance(ciphertext, bytes) or not ciphertext or ciphertext == payload:
                raise OfflineDeniedError("encryption_required")
            self._sequence += 1
            envelope = SyncEnvelope(execution, ciphertext, _digest(ciphertext), self._sequence)
            self._records[execution.execution_id] = envelope
            return envelope

    def decrypt(self, execution_id: str) -> bytes:
        _bounded(execution_id, "execution_id")
        with self._lock:
            envelope = self._records[execution_id]
            aad = f"noryx7/offline-sync/v1/{execution_id}".encode("utf-8")
            return self._cipher.decrypt(envelope.ciphertext, aad=aad)

    def acknowledge(self, execution_id: str) -> None:
        with self._lock:
            self._records.pop(_bounded(execution_id, "execution_id"), None)

    def snapshot(self) -> tuple[SyncEnvelope, ...]:
        with self._lock:
            return tuple(self._records.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)


class OfflineRuntime:
    """Coordinates offline admission, verified execution, commit and secure sync."""

    def __init__(
        self,
        *,
        recovery: RecoveryLike,
        policy: OfflinePolicy,
        verifier: OfflineVerifier,
        cipher: OfflineCipher,
        clock: Callable[[], int],
        max_snapshot_age: int = MAX_SNAPSHOT_AGE,
    ) -> None:
        if max_snapshot_age < 0:
            raise ValueError("invalid_max_snapshot_age")
        self._recovery = recovery
        self._policy = policy
        self._verifier = verifier
        self._clock = clock
        self._queue = OfflineSyncQueue(cipher)
        self._snapshot: OfflineSnapshot | None = None
        self._state = OfflineState.ONLINE
        self._lock = threading.RLock()
        self._max_snapshot_age = max_snapshot_age

    @property
    def state(self) -> OfflineState:
        with self._lock:
            return self._state

    @property
    def queue(self) -> OfflineSyncQueue:
        return self._queue

    def install_snapshot(self, snapshot: OfflineSnapshot) -> None:
        if not snapshot.verify_integrity():
            raise OfflineDeniedError("invalid_offline_snapshot")
        now = self._clock()
        if snapshot.issued_at > now or now - snapshot.issued_at > self._max_snapshot_age:
            raise OfflineDeniedError("stale_offline_snapshot")
        with self._lock:
            self._snapshot = snapshot
            self._state = OfflineState.READY

    def disconnect(self) -> None:
        with self._lock:
            if self._snapshot is None:
                self._state = OfflineState.DISCONNECTED
                return
            self._state = OfflineState.READY

    def execute(
        self,
        *,
        execution: OfflineExecution,
        payload: bytes,
        result: object,
        commit: Callable[[OfflineExecution, object], None],
    ) -> SyncEnvelope:
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
            raise ValueError("invalid_payload")
        with self._lock:
            snapshot = self._snapshot
            if snapshot is None or not snapshot.verify_integrity():
                raise OfflineDeniedError("offline_snapshot_required")
            if snapshot.principal_id != execution.principal_id:
                raise OfflineDeniedError("offline_identity_mismatch")
            if execution.capability not in snapshot.capabilities:
                raise OfflineDeniedError("offline_capability_denied")
            if _digest(payload) != execution.payload_digest:
                raise OfflineDeniedError("offline_payload_mismatch")
            if not self._policy.authorize(principal_id=execution.principal_id, operation=execution.operation, offline=True):
                raise OfflineDeniedError("offline_policy_denied")
            recovery_state, epoch = self._recovery.snapshot()
            if str(getattr(recovery_state, "value", recovery_state)).lower() not in {"normal", "verified"}:
                self._state = OfflineState.RECOVERY
                raise OfflineDeniedError("offline_recovery_denied")
            self._state = OfflineState.EXECUTING

        try:
            def critical() -> None:
                if not self._verifier.verify(result):
                    raise OfflineDeniedError("offline_result_unverified")
                commit(execution, result)

            self._recovery.require_normal(expected_epoch=epoch)
            if str(getattr(recovery_state, "value", recovery_state)).lower() == "verified":
                # A VERIFIED recovery state is safe only if its controller permits
                # normal-operation admission; require_normal is the authoritative gate.
                pass
            critical()
            envelope = self._queue.enqueue(execution, payload)
        except Exception:
            with self._lock:
                self._state = OfflineState.RECOVERY
            raise
        with self._lock:
            self._state = OfflineState.SYNC_PENDING
        return envelope

    def reconnect(self, *, authenticated: bool, channel_verified: bool) -> tuple[SyncEnvelope, ...]:
        if not authenticated or not channel_verified:
            raise OfflineDeniedError("secure_reconnect_required")
        with self._lock:
            if self._snapshot is None or not self._snapshot.verify_integrity():
                raise OfflineDeniedError("offline_snapshot_required")
            self._state = OfflineState.SYNCING
            return self._queue.snapshot()

    def acknowledge_synced(self, execution_id: str, *, conflict: bool = False) -> None:
        with self._lock:
            if conflict:
                self._state = OfflineState.CONFLICT
                raise OfflineConflictError("offline_sync_conflict")
            self._queue.acknowledge(execution_id)
            self._state = OfflineState.SYNC_PENDING if len(self._queue) else OfflineState.ONLINE
