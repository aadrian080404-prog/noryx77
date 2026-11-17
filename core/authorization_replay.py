"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from contextlib import closing

MAX_TOKENS = 4096
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes cryptographic authorization tokens exactly once, fail-closed."""

    def __init__(self, *, max_tokens: int = MAX_TOKENS) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        self._max_tokens = max_tokens
        self._consumed: set[bytes] = set()
        self._lock = threading.Lock()

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def consumed_count(self) -> int:
        with self._lock:
            return len(self._consumed)

    def consume(self, token: bytes) -> bool:
        """Atomically consume token; return False for malformed/replayed/full input."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if token in self._consumed:
                return False
            if len(self._consumed) >= self._max_tokens:
                return False
            self._consumed.add(bytes(token))
            return True

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            return token in self._consumed


class SQLiteAuthorizationReplayGuard(AuthorizationReplayGuard):
    """Durable, cross-instance single-use guard backed by SQLite transactions.

    Only SHA-256 token fingerprints are persisted; raw authorization tokens are
    never written to disk. Entries are intentionally not expired: deleting a
    consumed token would make an old authorization replayable. Once capacity is
    reached, new privileged actions are rejected until an operator provisions a
    larger, migrated store. Each operation opens its own connection so separate
    runtime processes coordinate through SQLite's transaction and unique index.
    """

    def __init__(self, database_path: str | os.PathLike[str], *, max_tokens: int = MAX_TOKENS) -> None:
        super().__init__(max_tokens=max_tokens)
        try:
            path = os.fspath(database_path)
        except TypeError as exc:
            raise ValueError("invalid_replay_database_path") from exc
        if not isinstance(path, str) or not path.strip() or path == ":memory:":
            raise ValueError("persistent_replay_database_required")
        self._database_path = path
        try:
            with closing(self._connect()) as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS authorization_replay_tokens ("
                    "token_hash TEXT PRIMARY KEY, consumed_at REAL NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS authorization_replay_metadata ("
                    "singleton INTEGER PRIMARY KEY CHECK (singleton = 1), "
                    "schema_version INTEGER NOT NULL, max_tokens INTEGER NOT NULL)"
                )
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT schema_version, max_tokens FROM authorization_replay_metadata "
                    "WHERE singleton = 1"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO authorization_replay_metadata "
                        "(singleton, schema_version, max_tokens) VALUES (1, 1, ?)",
                        (self._max_tokens,),
                    )
                elif row != (1, self._max_tokens):
                    raise ValueError("replay_store_configuration_mismatch")
                connection.commit()
        except sqlite3.Error as exc:
            raise ValueError("replay_store_initialization_failed") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @property
    def consumed_count(self) -> int:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT COUNT(*) FROM authorization_replay_tokens"
                ).fetchone()
                return int(row[0])
        except (sqlite3.Error, TypeError, ValueError):
            return self._max_tokens

    def consume(self, token: bytes) -> bool:
        """Persist a token fingerprint atomically; fail closed on any DB error."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        fingerprint = hashlib.sha256(token).hexdigest()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT 1 FROM authorization_replay_tokens WHERE token_hash = ?",
                    (fingerprint,),
                ).fetchone()
                if existing is not None:
                    connection.rollback()
                    return False
                count = connection.execute(
                    "SELECT COUNT(*) FROM authorization_replay_tokens"
                ).fetchone()[0]
                if count >= self._max_tokens:
                    connection.rollback()
                    return False
                connection.execute(
                    "INSERT INTO authorization_replay_tokens (token_hash, consumed_at) "
                    "VALUES (?, CAST(strftime('%s','now') AS REAL))",
                    (fingerprint,),
                )
                connection.commit()
                return True
        except sqlite3.Error:
            return False

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        fingerprint = hashlib.sha256(token).hexdigest()
        try:
            with self._connect() as connection:
                return connection.execute(
                    "SELECT 1 FROM authorization_replay_tokens WHERE token_hash = ?",
                    (fingerprint,),
                ).fetchone() is not None
        except sqlite3.Error:
            return False
