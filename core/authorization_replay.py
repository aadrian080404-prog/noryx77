"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import sqlite3
import threading
import math
import time

MAX_TOKENS = 1_000_000
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes authorization tokens once; persistent mode survives process restarts.

    In-memory mode is intended for tests and non-privileged development only.
    High-risk RuntimeEngine actions require a file-backed SQLite guard.
    """

    SCHEMA_VERSION = 2

    def __init__(self, *, max_tokens: int = MAX_TOKENS, path: str | None = None) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ValueError("invalid_replay_guard_path")
        self._max_tokens = max_tokens
        self._path = path
        self._consumed: dict[bytes, float] = {}
        self._lock = threading.RLock()
        self._db: sqlite3.Connection | None = None
        self._closed = False
        if path is not None and path != ":memory:":
            db = sqlite3.connect(
                path,
                timeout=30,
                isolation_level=None,
                check_same_thread=False,
            )
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=FULL")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS replay_guard_tokens ("
                    "token BLOB PRIMARY KEY, expires_at REAL NOT NULL) WITHOUT ROWID"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS replay_guard_meta ("
                    "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                row = db.execute(
                    "SELECT value FROM replay_guard_meta WHERE key='max_tokens'"
                ).fetchone()
                if row is None:
                    db.execute(
                        "INSERT INTO replay_guard_meta(key,value) VALUES('max_tokens',?)",
                        (str(max_tokens),),
                    )
                    db.execute(
                        "INSERT INTO replay_guard_meta(key,value) VALUES('schema_version',?)",
                        (str(self.SCHEMA_VERSION),),
                    )
                elif row[0] != str(max_tokens):
                    raise ValueError("replay_guard_capacity_mismatch")
                schema = db.execute(
                    "SELECT value FROM replay_guard_meta WHERE key='schema_version'"
                ).fetchone()
                if schema is None or schema[0] != str(self.SCHEMA_VERSION):
                    raise ValueError("unsupported_replay_guard_schema")
            except Exception:
                db.close()
                raise
            self._db = db

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def durable(self) -> bool:
        return self._db is not None and not self._closed

    @property
    def consumed_count(self) -> int:
        with self._lock:
            if self._closed:
                raise RuntimeError("replay_guard_closed")
            if self._db is None:
                return len(self._consumed)
            try:
                return int(self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_tokens"
                ).fetchone()[0])
            except sqlite3.Error as exc:
                raise RuntimeError("replay_guard_storage_unavailable") from exc

    def consume(self, token: bytes, *, expires_at: float, now: float | None = None) -> bool:
        """Atomically consume a token until expiry; expired rows are reclaimed safely."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in (expires_at, now)) or expires_at <= now:
            return False
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                self._consumed = {key: expiry for key, expiry in self._consumed.items() if expiry > now}
                if token in self._consumed or len(self._consumed) >= self._max_tokens:
                    return False
                self._consumed[bytes(token)] = float(expires_at)
                return True
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute("DELETE FROM replay_guard_tokens WHERE expires_at<=?", (float(now),))
                exists = self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=? AND expires_at>?",
                    (sqlite3.Binary(token), float(now)),
                ).fetchone()
                if exists is not None:
                    self._db.execute("ROLLBACK")
                    return False
                count = self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_tokens"
                ).fetchone()[0]
                if count >= self._max_tokens:
                    self._db.execute("ROLLBACK")
                    return False
                self._db.execute(
                    "INSERT INTO replay_guard_tokens(token,expires_at) VALUES(?,?)",
                    (sqlite3.Binary(token), float(expires_at)),
                )
                self._db.execute("COMMIT")
                return True
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def contains(self, token: bytes, *, now: float | None = None) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(float(now)):
            return True
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                expiry = self._consumed.get(token)
                if expiry is None:
                    return False
                if expiry <= now:
                    self._consumed.pop(token, None)
                    return False
                return True
            try:
                return self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=? AND expires_at>?",
                    (sqlite3.Binary(token), float(now)),
                ).fetchone() is not None
            except sqlite3.Error:
                return False

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            self._closed = True
