"""SQLite-backed fencing enforced at a protected resource boundary.

This is a single-host durability adapter, not distributed consensus. Every
write is serialized by SQLite and checks the active generation in the same
transaction that records the idempotent operation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import sqlite3
from typing import Union


@dataclass(frozen=True)
class DurableAppliedOperation:
    resource_id: str
    operation_id: str
    fencing_token: int
    payload_digest: str
    version: int


class SQLiteFencedResource:
    def __init__(self, database: Union[str, bytes], *, timeout: float = 5.0) -> None:
        if not isinstance(database, (str, bytes)) or not database:
            raise ValueError("database_path_required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout_must_be_finite_and_positive")
        self._database = database
        self._timeout = float(timeout)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS fenced_resources (
                    resource_id TEXT PRIMARY KEY,
                    highest_token INTEGER NOT NULL CHECK(highest_token >= 0),
                    version INTEGER NOT NULL CHECK(version >= 0)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS fenced_operations (
                    resource_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL CHECK(fencing_token > 0),
                    payload_digest TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK(version > 0),
                    PRIMARY KEY(resource_id, operation_id),
                    UNIQUE(resource_id, version),
                    FOREIGN KEY(resource_id) REFERENCES fenced_resources(resource_id)
                )"""
            )

    def _connect(self):
        connection = sqlite3.connect(self._database, timeout=self._timeout, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=%d" % int(self._timeout * 1000))
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @staticmethod
    def _validate_resource(resource_id: str) -> None:
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("resource_id_required")

    @staticmethod
    def _validate_token(token: int) -> None:
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            raise ValueError("fencing_token_must_be_positive_integer")

    def activate(self, resource_id: str, token: int) -> int:
        self._validate_resource(resource_id)
        self._validate_token(token)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT highest_token FROM fenced_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO fenced_resources(resource_id, highest_token, version) VALUES(?,?,0)",
                    (resource_id, token),
                )
            else:
                if token <= row[0]:
                    connection.rollback()
                    raise PermissionError("fencing_token_not_monotonic")
                connection.execute(
                    "UPDATE fenced_resources SET highest_token=? WHERE resource_id=?",
                    (token, resource_id),
                )
            connection.commit()
        return token

    def apply(self, resource_id: str, token: int, operation_id: str, payload: bytes) -> DurableAppliedOperation:
        self._validate_resource(resource_id)
        self._validate_token(token)
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id_required")
        if not isinstance(payload, bytes):
            raise TypeError("payload_must_be_bytes")
        digest = hashlib.sha256(payload).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                """SELECT fencing_token, payload_digest, version
                   FROM fenced_operations WHERE resource_id=? AND operation_id=?""",
                (resource_id, operation_id),
            ).fetchone()
            if previous is not None:
                if previous[1] != digest:
                    connection.rollback()
                    raise PermissionError("idempotency_key_payload_conflict")
                connection.commit()
                return DurableAppliedOperation(resource_id, operation_id, previous[0], previous[1], previous[2])

            resource = connection.execute(
                "SELECT highest_token, version FROM fenced_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if resource is None or token != resource[0]:
                connection.rollback()
                raise PermissionError("stale_or_unactivated_fencing_token")
            version = resource[1] + 1
            connection.execute(
                "UPDATE fenced_resources SET version=? WHERE resource_id=?",
                (version, resource_id),
            )
            connection.execute(
                """INSERT INTO fenced_operations
                   (resource_id, operation_id, fencing_token, payload_digest, version)
                   VALUES(?,?,?,?,?)""",
                (resource_id, operation_id, token, digest, version),
            )
            connection.commit()
        return DurableAppliedOperation(resource_id, operation_id, token, digest, version)

    def snapshot(self, resource_id: str) -> tuple[int, int]:
        self._validate_resource(resource_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT highest_token, version FROM fenced_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
        return (0, 0) if row is None else (row[0], row[1])
