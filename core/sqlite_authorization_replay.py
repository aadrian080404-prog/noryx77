"""Durable bounded single-use replay protection backed by SQLite."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from core.authorization_replay import MAX_TOKENS, TOKEN_SIZE


class SQLiteAuthorizationReplayGuard:
    """Persist consumed authorization digests across process restarts.

    Tokens are retained permanently. Once the configured bound is reached,
    new tokens fail closed; reclamation requires a separately designed
    epoch/monotonic-witness policy and is intentionally not automatic.
    """

    def __init__(self, db_path: str | Path, *, max_tokens: int = MAX_TOKENS) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        self.db_path = str(db_path)
        self._max_tokens = max_tokens
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.db_path, timeout=5.0, check_same_thread=False, isolation_level=None
        )
        with self._lock:
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS consumed_authorization_tokens ("
                "token BLOB PRIMARY KEY, consumed_at REAL NOT NULL, "
                "CHECK(length(token)=32))"
            )
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS authorization_replay_guard_config ("
                "singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                "max_tokens INTEGER NOT NULL CHECK(max_tokens BETWEEN 1 AND 4096))"
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO authorization_replay_guard_config(singleton, max_tokens) "
                "VALUES (1, ?)",
                (max_tokens,),
            )
            configured = self._conn.execute(
                "SELECT max_tokens FROM authorization_replay_guard_config WHERE singleton=1"
            ).fetchone()
            if configured is None or int(configured[0]) != max_tokens:
                self._conn.close()
                raise ValueError("replay_guard_capacity_mismatch")

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def consumed_count(self) -> int:
        with self._lock:
            return int(self._conn.execute(
                "SELECT COUNT(*) FROM consumed_authorization_tokens"
            ).fetchone()[0])

    def consume(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                count = int(self._conn.execute(
                    "SELECT COUNT(*) FROM consumed_authorization_tokens"
                ).fetchone()[0])
                if count >= self._max_tokens:
                    self._conn.commit()
                    return False
                try:
                    self._conn.execute(
                        "INSERT INTO consumed_authorization_tokens(token, consumed_at) "
                        "VALUES (?, ?)",
                        (bytes(token), time.time()),
                    )
                except sqlite3.IntegrityError:
                    self._conn.rollback()
                    return False
                self._conn.commit()
                return True
            except Exception:
                if self._conn.in_transaction:
                    self._conn.rollback()
                raise

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM consumed_authorization_tokens WHERE token=?",
                (token,),
            ).fetchone()
        return row is not None

    def close(self) -> None:
        with self._lock:
            self._conn.close()
