"""Global state/memory and identity/authorization contracts for NORYX7."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from threading import RLock


MAX_RECORD_BYTES = 1 << 20
MAX_RECORDS = 1_000_000
MAX_REPLICAS = 64
MAX_CAPABILITIES = 256


class MemoryLevel(str, Enum):
    L0_DEVICE = "l0_device"
    L1_EDGE = "l1_edge"
    L2_REGIONAL = "l2_regional"
    L3_DISTRIBUTED = "l3_distributed"
    L4_LONG_TERM = "l4_long_term"
    L5_ARCHIVAL = "l5_archival"


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    level: MemoryLevel
    version: int
    payload_digest: str
    replicas: tuple[str, ...]
    provenance_digest: str

    @property
    def payload(self) -> bytes:
        """Compatibility view exposing only the metadata digest, never raw payload."""
        return b"metadata_digest=" + self.payload_digest.encode("ascii")

    def __post_init__(self) -> None:
        _id(self.record_id)
        if not isinstance(self.level, MemoryLevel) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("invalid_memory_record")
        _digest(self.payload_digest, "payload_digest")
        _digest(self.provenance_digest, "provenance_digest")
        if not isinstance(self.replicas, tuple) or not self.replicas or len(self.replicas) > MAX_REPLICAS:
            raise ValueError("invalid_replica_set")
        if any(not isinstance(replica, str) or not replica.strip() for replica in self.replicas):
            raise ValueError("invalid_replica_id")


def _id(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > 256:
        raise ValueError("invalid_identifier")
    return value


def _digest(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid_{name}")


class GlobalMemoryFabric:
    """Bounded state index; encryption/durable storage/transport remain adapters."""
    def __init__(self, max_records: int = MAX_RECORDS) -> None:
        if not isinstance(max_records, int) or not 1 <= max_records <= MAX_RECORDS:
            raise ValueError("invalid_memory_limit")
        self._max = max_records
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    def put(self, record_id: str, level: MemoryLevel, payload: bytes, provenance: bytes, replicas: tuple[str, ...]) -> MemoryRecord:
        _id(record_id)
        if not isinstance(level, MemoryLevel) or not isinstance(payload, bytes) or not isinstance(provenance, bytes):
            raise TypeError("invalid_memory_input")
        if not payload or len(payload) > MAX_RECORD_BYTES or not provenance or len(provenance) > MAX_RECORD_BYTES:
            raise ValueError("memory_payload_bounds_exceeded")
        if not isinstance(replicas, tuple) or not replicas or len(replicas) > MAX_REPLICAS:
            raise ValueError("invalid_replica_set")
        with self._lock:
            previous = self._records.get(record_id)
            if previous is None and len(self._records) >= self._max:
                raise MemoryError("global_memory_capacity_exceeded")
            version = 1 if previous is None else previous.version + 1
            record = MemoryRecord(record_id, level, version, sha256(payload).hexdigest(), replicas, sha256(provenance).hexdigest())
            self._records[record_id] = record
            return record

    def get(self, record_id: str) -> MemoryRecord:
        _id(record_id)
        with self._lock:
            try:
                return self._records[record_id]
            except KeyError as exc:
                raise LookupError("memory_record_not_found") from exc

    def require_redundancy(self, record_id: str, minimum_replicas: int = 2) -> MemoryRecord:
        record = self.get(record_id)
        if not isinstance(minimum_replicas, int) or minimum_replicas < 1:
            raise ValueError("invalid_replica_requirement")
        if len(record.replicas) < minimum_replicas:
            raise RuntimeError("memory_redundancy_insufficient")
        return record

    def snapshot(self) -> tuple[MemoryRecord, ...]:
        with self._lock:
            return tuple(self._records.values())


@dataclass(frozen=True)
class IdentityAuthorization:
    identity_id: str
    session_id: str
    device_id: str
    role: str
    capabilities: tuple[str, ...]
    policy_digest: str
    authorization_digest: str

    def __post_init__(self) -> None:
        for value in (self.identity_id, self.session_id, self.device_id, self.role):
            _id(value)
        if not isinstance(self.capabilities, tuple) or len(self.capabilities) > MAX_CAPABILITIES:
            raise ValueError("invalid_capabilities")
        if any(not isinstance(value, str) or not value.strip() for value in self.capabilities):
            raise ValueError("invalid_capability")
        _digest(self.policy_digest, "policy_digest")
        _digest(self.authorization_digest, "authorization_digest")


class GlobalIdentityAuthorizationFabric:
    """Index for identity/session/device/capability decisions; never grants authority implicitly."""
    def __init__(self) -> None:
        self._entries: dict[str, IdentityAuthorization] = {}
        self._lock = RLock()

    def bind(self, authorization: IdentityAuthorization) -> None:
        if not isinstance(authorization, IdentityAuthorization):
            raise TypeError("authorization_required")
        with self._lock:
            previous = self._entries.get(authorization.session_id)
            if previous is not None and (previous.identity_id != authorization.identity_id or previous.device_id != authorization.device_id):
                raise PermissionError("session_identity_binding_mismatch")
            self._entries[authorization.session_id] = authorization

    def authorize(self, session_id: str, capability: str, policy_digest: str) -> IdentityAuthorization:
        _id(session_id); _id(capability); _digest(policy_digest, "policy_digest")
        with self._lock:
            authorization = self._entries.get(session_id)
            if authorization is None or authorization.policy_digest != policy_digest:
                raise PermissionError("authorization_not_valid")
            if capability not in authorization.capabilities:
                raise PermissionError("capability_not_granted")
            return authorization

    def revoke(self, session_id: str) -> None:
        _id(session_id)
        with self._lock:
            self._entries.pop(session_id, None)

    def snapshot(self) -> tuple[IdentityAuthorization, ...]:
        with self._lock:
            return tuple(self._entries.values())
