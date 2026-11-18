import os
import sqlite3
from pathlib import Path

from .audit import AuditLog


class SQLiteAuditLog(AuditLog):
    """Durable append-only audit chain coordinated by SQLite transactions.

    This coordinates processes that open the same database file. It is not a
    consensus protocol and does not coordinate independent databases/devices.
    """

    _SCHEMA_VERSION = 1

    def __init__(self, database_path: str | os.PathLike[str]):
        if isinstance(database_path, (str, os.PathLike)):
            raw_path = os.fspath(database_path)
        else:
            raise ValueError("persistent_audit_database_required")
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path == ":memory:":
            raise ValueError("persistent_audit_database_required")
        self.database_path = str(Path(raw_path))
        super().__init__()
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS noryx7_audit_metadata "
                    "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS noryx7_audit_events "
                    "(sequence INTEGER PRIMARY KEY, entry_json TEXT NOT NULL, "
                    "previous_digest TEXT NOT NULL, digest TEXT NOT NULL UNIQUE)"
                )
                row = connection.execute(
                    "SELECT value FROM noryx7_audit_metadata WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    existing = connection.execute(
                        "SELECT COUNT(*) FROM noryx7_audit_events"
                    ).fetchone()[0]
                    if existing:
                        raise ValueError("audit_schema_metadata_missing")
                    connection.execute(
                        "INSERT INTO noryx7_audit_metadata(key, value) VALUES('schema_version', ?)",
                        (str(self._SCHEMA_VERSION),),
                    )
                elif row[0] != str(self._SCHEMA_VERSION):
                    raise ValueError("audit_schema_version_mismatch")
                connection.execute(
                    "CREATE TRIGGER IF NOT EXISTS noryx7_audit_events_no_update "
                    "BEFORE UPDATE ON noryx7_audit_events "
                    "BEGIN SELECT RAISE(ABORT, 'audit_events_are_append_only'); END"
                )
                connection.execute(
                    "CREATE TRIGGER IF NOT EXISTS noryx7_audit_events_no_delete "
                    "BEFORE DELETE ON noryx7_audit_events "
                    "BEGIN SELECT RAISE(ABORT, 'audit_events_are_append_only'); END"
                )
                connection.commit()
                try:
                    os.chmod(self.database_path, 0o600)
                except OSError:
                    pass
                self._refresh_cache_locked(connection)
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _refresh_cache_locked(self, connection: sqlite3.Connection | None = None) -> None:
        owns_connection = connection is None
        if connection is None:
            connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT entry_json, digest FROM noryx7_audit_events ORDER BY sequence"
            ).fetchall()
            events = []
            digests = []
            for entry_json, digest in rows:
                entry = __import__("json").loads(entry_json)
                if not isinstance(entry, dict):
                    raise ValueError("audit_record_malformed")
                events.append(entry)
                digests.append(digest)
            self._events = events
            self._digests = digests
        finally:
            if owns_connection:
                connection.close()

    def _verify_integrity_locked(self) -> bool:
        try:
            self._refresh_cache_locked()
        except (sqlite3.Error, ValueError, TypeError):
            return False
        return super()._verify_integrity_locked()

    def record(self, event: str, **data):
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        import copy
        import json

        stored = copy.deepcopy({"event": event, **data})
        # Validate and canonicalize before opening the write transaction.
        json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT sequence, digest FROM noryx7_audit_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if row is None else row[0] + 1
                previous_digest = self._GENESIS if row is None else row[1]
                digest = self._digest(stored, previous_digest)
                entry_json = json.dumps(
                    stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                connection.execute(
                    "INSERT INTO noryx7_audit_events(sequence, entry_json, previous_digest, digest) "
                    "VALUES(?, ?, ?, ?)",
                    (sequence, entry_json, previous_digest, digest),
                )
                connection.commit()
                self._refresh_cache_locked(connection)
                return copy.deepcopy(stored)
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def snapshot(self):
        with self._lock:
            self._refresh_cache_locked()
            return super().snapshot()

    def verify_integrity(self) -> bool:
        with self._lock:
            return self._verify_integrity_locked()

    def digest(self) -> str:
        with self._lock:
            try:
                self._refresh_cache_locked()
            except (sqlite3.Error, ValueError, TypeError):
                raise RuntimeError("audit_storage_unavailable")
            return super().digest()
