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


class SQLiteKeyLifecycle:
    """SQLite-backed durable key metadata; raw key material stays external.

    Transactions serialize lifecycle transitions across processes sharing this
    database. This does not authenticate the database or detect restoration of
    an old database snapshot; use independent integrity/anti-rollback controls
    for a production trust root.
    """

    def __init__(self, path: str):
        import sqlite3
        from pathlib import Path

        if not isinstance(path, str) or not path.strip():
            raise ValueError("key_lifecycle_database_path_required")
        self._lock = RLock()
        self._closed = False
        self._db = sqlite3.connect(
            str(Path(path)), timeout=30, isolation_level=None, check_same_thread=False
        )
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS key_lifecycle ("
                "key_id TEXT PRIMARY KEY, version INTEGER NOT NULL, state TEXT NOT NULL)"
            )
            self._validate_rows()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    @staticmethod
    def _validate_key_id(key_id: object) -> str:
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id.encode("utf-8")) > 256:
            raise ValueError("invalid_key_id")
        return key_id

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("key_lifecycle_closed")

    def _validate_rows(self) -> None:
        for key_id, version, state in self._db.execute(
            "SELECT key_id, version, state FROM key_lifecycle"
        ):
            if (
                not isinstance(key_id, str) or not key_id.strip()
                or isinstance(version, bool) or not isinstance(version, int) or version < 1
                or state not in {item.value for item in KeyState}
            ):
                raise RuntimeError("key_lifecycle_database_corrupt")

    @staticmethod
    def _record(row) -> KeyRecord:
        if row is None:
            raise KeyError("unknown_key_id")
        key_id, version, state = row
        try:
            return KeyRecord(key_id, version, KeyState(state))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("key_lifecycle_database_corrupt") from exc

    def _read(self, key_id: str) -> KeyRecord:
        self._validate_key_id(key_id)
        return self._record(self._db.execute(
            "SELECT key_id, version, state FROM key_lifecycle WHERE key_id=?", (key_id,)
        ).fetchone())

    def register(self, key_id: str, *, version: int = 1) -> KeyRecord:
        self._validate_key_id(key_id)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("invalid_key_version")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO key_lifecycle(key_id,version,state) VALUES(?,?,?)",
                    (key_id, version, KeyState.ACTIVE.value),
                )
                self._db.execute("COMMIT")
            except Exception as exc:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("key_id_already_registered") from exc
                raise
            return KeyRecord(key_id, version, KeyState.ACTIVE)

    def rotate(self, key_id: str) -> KeyRecord:
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._read(key_id)
                if current.state is KeyState.REVOKED:
                    raise PermissionError("revoked_key_cannot_rotate")
                if current.state is KeyState.RETIRING:
                    raise PermissionError("retiring_key_cannot_reactivate")
                updated = KeyRecord(key_id, current.version + 1, KeyState.ACTIVE)
                self._db.execute(
                    "UPDATE key_lifecycle SET version=?,state=? WHERE key_id=?",
                    (updated.version, updated.state.value, key_id),
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def retire(self, key_id: str) -> KeyRecord:
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._read(key_id)
                if current.state is KeyState.REVOKED:
                    raise PermissionError("revoked_key_cannot_retire")
                updated = KeyRecord(key_id, current.version, KeyState.RETIRING)
                self._db.execute(
                    "UPDATE key_lifecycle SET state=? WHERE key_id=?",
                    (updated.state.value, key_id),
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def revoke(self, key_id: str) -> KeyRecord:
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._read(key_id)
                updated = KeyRecord(key_id, current.version, KeyState.REVOKED)
                self._db.execute(
                    "UPDATE key_lifecycle SET state=? WHERE key_id=?",
                    (updated.state.value, key_id),
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def require_active(self, key_id: str) -> KeyRecord:
        with self._lock:
            self._ensure_open()
            record = self._read(key_id)
            if record.state is not KeyState.ACTIVE:
                raise PermissionError("key_not_active")
            return record

    def snapshot(self) -> tuple[KeyRecord, ...]:
        with self._lock:
            self._ensure_open()
            rows = self._db.execute(
                "SELECT key_id, version, state FROM key_lifecycle ORDER BY key_id"
            ).fetchall()
            return tuple(self._record(row) for row in rows)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
