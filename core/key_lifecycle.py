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


class SQLiteKeyLifecycle(KeyLifecycle):
    """Crash-persistent key policy metadata; never stores key material.

    The actual cryptographic key remains in an external KMS/HSM adapter. This
    class serializes state transitions across processes using SQLite write
    transactions and fails closed on malformed persisted rows.
    """

    def __init__(self, database_path: str) -> None:
        import sqlite3

        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("key_lifecycle_database_path_required")
        self._lock = RLock()
        self._closed = False
        self._db = sqlite3.connect(
            database_path, timeout=30, isolation_level=None, check_same_thread=False
        )
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS key_lifecycle (
                    key_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL CHECK(version > 0),
                    state TEXT NOT NULL CHECK(state IN ('active','retiring','revoked'))
                )
            """)
            self._validate_rows()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("key_lifecycle_closed")

    @staticmethod
    def _validate_key_id(key_id: str) -> None:
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        try:
            size = len(key_id.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_key_id") from exc
        if size > 256:
            raise ValueError("invalid_key_id")

    def _validate_rows(self) -> None:
        for key_id, version, state in self._db.execute(
            "SELECT key_id, version, state FROM key_lifecycle"
        ):
            try:
                self._validate_key_id(key_id)
            except ValueError as exc:
                raise RuntimeError("key_lifecycle_database_corrupt") from exc
            if (
                isinstance(version, bool) or not isinstance(version, int) or version < 1
                or state not in {item.value for item in KeyState}
            ):
                raise RuntimeError("key_lifecycle_database_corrupt")

    def _record(self, key_id: str) -> KeyRecord:
        row = self._db.execute(
            "SELECT key_id, version, state FROM key_lifecycle WHERE key_id=?",
            (key_id,),
        ).fetchone()
        if row is None:
            raise KeyError("unknown_key_id")
        try:
            return KeyRecord(row[0], row[1], KeyState(row[2]))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("key_lifecycle_database_corrupt") from exc

    def register(self, key_id: str, *, version: int = 1) -> KeyRecord:
        self._validate_key_id(key_id)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("invalid_key_version")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO key_lifecycle(key_id, version, state) VALUES (?, ?, 'active')",
                    (key_id, version),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
            return KeyRecord(key_id, version, KeyState.ACTIVE)

    def _transition(self, key_id: str, operation: str) -> KeyRecord:
        self._validate_key_id(key_id)
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._record(key_id)
                if operation == "rotate":
                    if current.state is KeyState.REVOKED:
                        raise PermissionError("revoked_key_cannot_rotate")
                    if current.state is KeyState.RETIRING:
                        raise PermissionError("retiring_key_cannot_reactivate")
                    updated = KeyRecord(key_id, current.version + 1, KeyState.ACTIVE)
                elif operation == "retire":
                    if current.state is KeyState.REVOKED:
                        raise PermissionError("revoked_key_cannot_retire")
                    updated = KeyRecord(key_id, current.version, KeyState.RETIRING)
                elif operation == "revoke":
                    updated = KeyRecord(key_id, current.version, KeyState.REVOKED)
                else:
                    raise ValueError("invalid_key_transition")
                cursor = self._db.execute(
                    "UPDATE key_lifecycle SET version=?, state=? "
                    "WHERE key_id=? AND version=? AND state=?",
                    (updated.version, updated.state.value, key_id,
                     current.version, current.state.value),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("key_lifecycle_transition_race")
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def rotate(self, key_id: str) -> KeyRecord:
        return self._transition(key_id, "rotate")

    def retire(self, key_id: str) -> KeyRecord:
        return self._transition(key_id, "retire")

    def revoke(self, key_id: str) -> KeyRecord:
        return self._transition(key_id, "revoke")

    def require_active(self, key_id: str) -> KeyRecord:
        self._validate_key_id(key_id)
        with self._lock:
            self._ensure_open()
            record = self._record(key_id)
            if record.state is not KeyState.ACTIVE:
                raise PermissionError("key_not_active")
            return record

    def snapshot(self) -> tuple[KeyRecord, ...]:
        with self._lock:
            self._ensure_open()
            rows = self._db.execute(
                "SELECT key_id, version, state FROM key_lifecycle ORDER BY key_id"
            ).fetchall()
            try:
                return tuple(KeyRecord(key_id, version, KeyState(state))
                             for key_id, version, state in rows)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("key_lifecycle_database_corrupt") from exc

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
