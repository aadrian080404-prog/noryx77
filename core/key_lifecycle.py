"""Explicit key lifecycle state machine for production key boundaries.

Key material remains outside NORYX7. The lifecycle manager tracks identity and
policy metadata only; an external KMS/HSM is responsible for key material.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock


class KeyState(str, Enum):
    ACTIVE = "active"
    RETIRING = "retiring"
    REVOKED = "revoked"


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    version: int
    state: KeyState


class ExternalKeyBoundary:
    """Interface implemented by a KMS/HSM adapter; never stores raw keys here."""

    def get_key(self, key_id: str, version: int) -> bytes:
        raise NotImplementedError


class KeyLifecycle:
    """Fail-closed lifecycle for rotation and revocation metadata."""

    def __init__(self) -> None:
        self._records: dict[str, KeyRecord] = {}
        self._lock = RLock()

    def register(self, key_id: str, *, version: int = 1) -> KeyRecord:
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("invalid_key_version")
        with self._lock:
            if key_id in self._records:
                raise ValueError("key_id_already_registered")
            record = KeyRecord(key_id, version, KeyState.ACTIVE)
            self._records[key_id] = record
            return record

    def rotate(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            if current.state is KeyState.REVOKED:
                raise PermissionError("revoked_key_cannot_rotate")
            if current.state is KeyState.RETIRING:
                raise PermissionError("retiring_key_cannot_reactivate")
            record = KeyRecord(key_id, current.version + 1, KeyState.ACTIVE)
            self._records[key_id] = record
            return record

    def retire(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            if current.state is KeyState.REVOKED:
                raise PermissionError("revoked_key_cannot_retire")
            record = KeyRecord(key_id, current.version, KeyState.RETIRING)
            self._records[key_id] = record
            return record

    def revoke(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            record = KeyRecord(key_id, current.version, KeyState.REVOKED)
            self._records[key_id] = record
            return record

    def require_active(self, key_id: str) -> KeyRecord:
        with self._lock:
            record = self._records.get(key_id)
            if record is None:
                raise KeyError("unknown_key_id")
            if record.state is not KeyState.ACTIVE:
                raise PermissionError("key_not_active")
            return record

    def snapshot(self) -> tuple[KeyRecord, ...]:
        with self._lock:
            return tuple(self._records.values())
