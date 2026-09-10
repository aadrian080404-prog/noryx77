"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

MAX_TOKENS = 4096
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes cryptographic authorization tokens exactly once, fail-closed."""

    def __init__(self, *, max_tokens: int = MAX_TOKENS, persistence_path: str | None = None) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        if persistence_path is not None and (not isinstance(persistence_path, str) or not persistence_path):
            raise ValueError("persistence path must be a non-empty string")
        self._max_tokens = max_tokens
        self._consumed: set[bytes] = set()
        self._lock = threading.Lock()
        self._db = None
        self._persistence_path = None
        if persistence_path is not None:
            self._persistence_path = str(Path(persistence_path).expanduser())
            Path(self._persistence_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self._persistence_path, isolation_level=None, check_same_thread=False)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("CREATE TABLE IF NOT EXISTS consumed_tokens (token BLOB PRIMARY KEY)")
            rows = self._db.execute("SELECT token FROM consumed_tokens LIMIT ?", (self._max_tokens,)).fetchall()
            self._consumed.update(bytes(row[0]) for row in rows if isinstance(row[0], bytes) and len(row[0]) == TOKEN_SIZE)

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def consumed_count(self) -> int:
        with self._lock:
            return len(self._consumed)

    @property
    def persistence_path(self) -> str | None:
        return self._persistence_path

    def consume(self, token: bytes) -> bool:
        """Atomically consume token; return False for malformed/replayed/full input."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if token in self._consumed:
                return False
            if len(self._consumed) >= self._max_tokens:
                return False
            if self._db is not None:
                try:
                    self._db.execute("INSERT INTO consumed_tokens(token) VALUES(?)", (sqlite3.Binary(token),))
                except sqlite3.IntegrityError:
                    self._consumed.add(bytes(token))
                    return False
                except sqlite3.Error:
                    return False
            self._consumed.add(bytes(token))
            return True

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if token in self._consumed:
                return True
            if self._db is not None:
                try:
                    row = self._db.execute("SELECT 1 FROM consumed_tokens WHERE token=? LIMIT 1", (sqlite3.Binary(token),)).fetchone()
                except sqlite3.Error:
                    return False
                if row is not None:
                    self._consumed.add(bytes(token))
                    return True
            return False

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
