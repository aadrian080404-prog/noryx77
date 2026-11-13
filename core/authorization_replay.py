"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import sqlite3
import threading

MAX_TOKENS = 4096
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes authorization tokens once; persistent mode survives process restarts.

    In-memory mode is intended for tests and non-privileged development only.
    High-risk RuntimeEngine actions require a file-backed SQLite guard.
    """

    SCHEMA_VERSION = 1

    def __init__(self, *, max_tokens: int = MAX_TOKENS, path: str | None = None) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ValueError("invalid_replay_guard_path")
        self._max_tokens = max_tokens
        self._path = path
        self._consumed: set[bytes] = set()
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
                    "token BLOB PRIMARY KEY) WITHOUT ROWID"
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

    def consume(self, token: bytes) -> bool:
        """Atomically consume token; malformed, replayed, full or storage-error inputs fail closed."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                if token in self._consumed or len(self._consumed) >= self._max_tokens:
                    return False
                self._consumed.add(bytes(token))
                return True
            try:
                self._db.execute("BEGIN IMMEDIATE")
                exists = self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=?",
                    (sqlite3.Binary(token),),
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
                    "INSERT INTO replay_guard_tokens(token) VALUES(?)",
                    (sqlite3.Binary(token),),
                )
                self._db.execute("COMMIT")
                return True
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                return token in self._consumed
            try:
                return self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=?",
                    (sqlite3.Binary(token),),
                ).fetchone() is not None
            except sqlite3.Error:
                return False

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            self._closed = True
