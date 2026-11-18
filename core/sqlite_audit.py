import copy
import json
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
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("persistent_audit_database_required")
        raw_path = os.fspath(database_path)
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
                if not self._read_and_verify_locked(connection):
                    raise ValueError("audit_integrity_failed")
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

    def _read_and_verify_locked(self, connection: sqlite3.Connection) -> bool:
        try:
            rows = connection.execute(
                "SELECT sequence, entry_json, previous_digest, digest "
                "FROM noryx7_audit_events ORDER BY sequence"
            ).fetchall()
            events = []
            digests = []
            previous_digest = self._GENESIS
            for expected_sequence, row in enumerate(rows, start=1):
                sequence, entry_json, stored_previous, stored_digest = row
                if sequence != expected_sequence or stored_previous != previous_digest:
                    return False
                entry = json.loads(entry_json)
                if not isinstance(entry, dict):
                    return False
                actual_digest = self._digest(entry, previous_digest)
                if actual_digest != stored_digest:
                    return False
                events.append(entry)
                digests.append(stored_digest)
                previous_digest = stored_digest
            self._events = events
            self._digests = digests
            return True
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
            return False

    def _verify_integrity_locked(self) -> bool:
        connection = self._connect()
        try:
            return self._read_and_verify_locked(connection)
        finally:
            connection.close()

    def record(self, event: str, **data):
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        stored = copy.deepcopy({"event": event, **data})
        try:
            json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("audit data must be JSON serializable") from exc

        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                if not self._read_and_verify_locked(connection):
                    raise ValueError("audit_integrity_failed")
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
                if not self._read_and_verify_locked(connection):
                    raise RuntimeError("audit_commit_verification_failed")
                return copy.deepcopy(stored)
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def snapshot(self):
        with self._lock:
            connection = self._connect()
            try:
                if not self._read_and_verify_locked(connection):
                    raise RuntimeError("audit_integrity_failed")
                return super().snapshot()
            finally:
                connection.close()

    def verify_integrity(self) -> bool:
        with self._lock:
            return self._verify_integrity_locked()

    def digest(self) -> str:
        with self._lock:
            if not self._verify_integrity_locked():
                raise RuntimeError("audit_integrity_failed")
            return super().digest()

    def checkpoint(self, provider, *, key_id: str):
        checkpoint = super().checkpoint(provider, key_id=key_id)
        if self.digest() != checkpoint.digest:
            raise ValueError("audit_chain_changed_during_checkpoint")
        return checkpoint

    def verify_checkpoint(self, checkpoint, provider) -> bool:
        if not self.verify_integrity() or self.digest() != getattr(checkpoint, "digest", None):
            return False
        if not super().verify_checkpoint(checkpoint, provider):
            return False
        return self.digest() == checkpoint.digest
