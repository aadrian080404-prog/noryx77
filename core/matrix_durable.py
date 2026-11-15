"""Crash-recoverable fencing for one protected resource.

SQLite is used as a local durability adapter, not as a distributed consensus
service. The database must reside on storage whose fsync/locking guarantees
match the deployment's threat and failure model.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import sqlite3
from pathlib import Path


@dataclass(frozen=True)
class DurableAppliedOperation:
    tenant_id: str
    operation_id: str
    fencing_token: int
    payload_digest: str
    version: int


class DurableFencedResource:
    """Atomically persist fencing epochs and idempotent effects in one SQLite DB."""

    def __init__(self, database: str | Path, resource_id: str, timeout: float = 5.0) -> None:
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("resource_id_required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("positive_database_timeout_required")
        self.database = str(database)
        self.resource_id = resource_id
        self.timeout = float(timeout)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = %d" % int(self.timeout * 1000))
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS matrix_resource_state (
                    resource_id TEXT PRIMARY KEY,
                    highest_token INTEGER NOT NULL CHECK(highest_token >= 0),
                    version INTEGER NOT NULL CHECK(version >= 0)
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS matrix_resource_operations (
                    resource_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    payload_digest TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    PRIMARY KEY(resource_id, tenant_id, operation_id)
                )"""
            )
            db.execute(
                "INSERT OR IGNORE INTO matrix_resource_state(resource_id, highest_token, version) VALUES (?, 0, 0)",
                (self.resource_id,),
            )

    @property
    def highest_token(self) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT highest_token FROM matrix_resource_state WHERE resource_id = ?",
                (self.resource_id,),
            ).fetchone()
        return int(row[0])

    @property
    def version(self) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT version FROM matrix_resource_state WHERE resource_id = ?",
                (self.resource_id,),
            ).fetchone()
        return int(row[0])

    def activate(self, token: int) -> int:
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            raise ValueError("fencing_token_must_be_positive_integer")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT highest_token FROM matrix_resource_state WHERE resource_id = ?",
                (self.resource_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("resource_state_missing")
            if token <= int(row[0]):
                raise PermissionError("fencing_token_not_monotonic")
            db.execute(
                "UPDATE matrix_resource_state SET highest_token = ? WHERE resource_id = ?",
                (token, self.resource_id),
            )
            db.commit()
        return token

    def apply(self, token: int, tenant_id: str, operation_id: str, payload: bytes) -> DurableAppliedOperation:
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            raise ValueError("fencing_token_must_be_positive_integer")
        for value, label in ((tenant_id, "tenant_id"), (operation_id, "operation_id")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(label + "_required")
        if not isinstance(payload, bytes):
            raise TypeError("payload_must_be_bytes")
        digest = hashlib.sha256(payload).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                """SELECT fencing_token, payload_digest, version
                   FROM matrix_resource_operations
                   WHERE resource_id = ? AND tenant_id = ? AND operation_id = ?""",
                (self.resource_id, tenant_id, operation_id),
            ).fetchone()
            if previous is not None:
                if previous[1] != digest:
                    raise PermissionError("idempotency_key_payload_conflict")
                db.commit()
                return DurableAppliedOperation(tenant_id, operation_id, int(previous[0]), digest, int(previous[2]))

            state = db.execute(
                "SELECT highest_token, version FROM matrix_resource_state WHERE resource_id = ?",
                (self.resource_id,),
            ).fetchone()
            if state is None or token != int(state[0]):
                raise PermissionError("stale_or_unactivated_fencing_token")
            version = int(state[1]) + 1
            db.execute(
                "UPDATE matrix_resource_state SET version = ? WHERE resource_id = ?",
                (version, self.resource_id),
            )
            db.execute(
                """INSERT INTO matrix_resource_operations
                   (resource_id, tenant_id, operation_id, fencing_token, payload_digest, version)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.resource_id, tenant_id, operation_id, token, digest, version),
            )
            db.commit()
        return DurableAppliedOperation(tenant_id, operation_id, token, digest, version)
