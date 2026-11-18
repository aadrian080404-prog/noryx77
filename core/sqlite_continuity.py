"""Crash-durable local storage for NORYX7 Continuity Protocol node state.

This store persists node fencing counters and isolation state across process
restarts. It is not a distributed consensus service or an anti-rollback anchor;
deployments requiring rollback detection must additionally configure a
monotonic external witness.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from threading import RLock

from .continuity import NodeContinuityRecord, NodeContinuityState


class SQLiteContinuityStore:
    SCHEMA_VERSION = 1

    def __init__(self, database_path: str, *, busy_timeout_ms: int = 5000) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("continuity_database_path_required")
        if database_path == ":memory:":
            raise ValueError("persistent_continuity_database_required")
        if (
            isinstance(busy_timeout_ms, bool)
            or not isinstance(busy_timeout_ms, int)
            or not 1 <= busy_timeout_ms <= 60000
        ):
            raise ValueError("continuity_busy_timeout_invalid")
        self.path = str(Path(database_path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._busy_timeout_ms = busy_timeout_ms
        self._lock = RLock()
        self._closed = False
        self._db = sqlite3.connect(
            self.path, timeout=busy_timeout_ms / 1000,
            isolation_level=None, check_same_thread=False,
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA trusted_schema=OFF")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS continuity_nodes (
                node_id TEXT PRIMARY KEY,
                identity_fingerprint TEXT NOT NULL,
                generation INTEGER NOT NULL CHECK(generation >= 0),
                sequence INTEGER NOT NULL CHECK(sequence >= 0),
                capabilities_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('active', 'isolated'))
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS continuity_meta (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL CHECK(value >= 0)
            )
        """)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute(
                "INSERT OR IGNORE INTO continuity_meta(key, value) VALUES ('schema_version', ?)",
                (self.SCHEMA_VERSION,),
            )
            version = self._db.execute(
                "SELECT value FROM continuity_meta WHERE key='schema_version'"
            ).fetchone()[0]
            if version != self.SCHEMA_VERSION:
                raise RuntimeError("continuity_schema_version_unsupported")
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            self._db.close()
            raise
        try:
            os.chmod(self.path, 0o600)
        except OSError as exc:
            self._db.close()
            raise RuntimeError("continuity_database_permissions_unavailable") from exc

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("continuity_store_closed")

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> NodeContinuityRecord:
        try:
            capabilities = json.loads(row["capabilities_json"])
            if (
                not isinstance(capabilities, list)
                or any(not isinstance(item, str) for item in capabilities)
            ):
                raise ValueError("invalid_capabilities")
            return NodeContinuityRecord(
                node_id=row["node_id"],
                identity_fingerprint=row["identity_fingerprint"],
                generation=row["generation"],
                sequence=row["sequence"],
                capabilities=tuple(capabilities),
                state=NodeContinuityState(row["state"]),
            )
        except (TypeError, ValueError, KeyError) as exc:
            raise RuntimeError("continuity_store_record_invalid") from exc

    @staticmethod
    def _record_values(record: NodeContinuityRecord) -> tuple:
        if not isinstance(record, NodeContinuityRecord):
            raise TypeError("continuity_record_required")
        capabilities = json.dumps(
            list(record.capabilities), ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        )
        return (
            record.node_id, record.identity_fingerprint, record.generation,
            record.sequence, capabilities, record.state.value,
        )

    def load_records(self) -> tuple[NodeContinuityRecord, ...]:
        with self._lock:
            self._ensure_open()
            rows = self._db.execute(
                "SELECT node_id, identity_fingerprint, generation, sequence, "
                "capabilities_json, state FROM continuity_nodes ORDER BY node_id"
            ).fetchall()
            return tuple(self._row_to_record(row) for row in rows)

    def insert_record(self, record: NodeContinuityRecord) -> None:
        values = self._record_values(record)
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO continuity_nodes "
                    "(node_id, identity_fingerprint, generation, sequence, capabilities_json, state) "
                    "VALUES (?, ?, ?, ?, ?, ?)", values,
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def replace_record(
        self, previous: NodeContinuityRecord, replacement: NodeContinuityRecord,
    ) -> bool:
        old = self._record_values(previous)
        new = self._record_values(replacement)
        if old[0] != new[0] or old[1] != new[1] or old[4] != new[4]:
            raise ValueError("continuity_record_identity_immutable")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                cursor = self._db.execute(
                    "UPDATE continuity_nodes SET generation=?, sequence=?, state=? "
                    "WHERE node_id=? AND identity_fingerprint=? AND generation=? "
                    "AND sequence=? AND capabilities_json=? AND state=?",
                    (new[2], new[3], new[5], old[0], old[1], old[2], old[3], old[4], old[5]),
                )
                accepted = cursor.rowcount == 1
                self._db.execute("COMMIT")
                return accepted
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
