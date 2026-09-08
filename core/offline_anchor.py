"""Durable monotonic anchor for offline rollback protection."""
from __future__ import annotations

import sqlite3
from threading import RLock


class MonotonicAnchor:
    """Persists the highest accepted snapshot epoch across process restarts.

    Production deployments should place this database behind protected storage
    or replace this adapter with a hardware-backed monotonic counter/TPM/HSM.
    """

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("anchor_path_required")
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("CREATE TABLE IF NOT EXISTS monotonic_anchor (id INTEGER PRIMARY KEY CHECK(id=1), issued_at INTEGER NOT NULL, snapshot_id TEXT NOT NULL)")
        self._lock = RLock()

    def accept(self, issued_at: int, snapshot_id: str) -> bool:
        if isinstance(issued_at, bool) or not isinstance(issued_at, int) or issued_at < 0:
            raise ValueError("invalid_anchor_epoch")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ValueError("invalid_snapshot_id")
        with self._lock:
            row = self._db.execute("SELECT issued_at,snapshot_id FROM monotonic_anchor WHERE id=1").fetchone()
            if row is not None:
                highest, highest_id = row
                if issued_at < highest or (issued_at == highest and snapshot_id != highest_id):
                    return False
                if issued_at == highest and snapshot_id == highest_id:
                    return True
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute("INSERT INTO monotonic_anchor(id,issued_at,snapshot_id) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET issued_at=excluded.issued_at,snapshot_id=excluded.snapshot_id", (issued_at, snapshot_id))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
            return True

    def current(self) -> tuple[int, str] | None:
        with self._lock:
            return self._db.execute("SELECT issued_at,snapshot_id FROM monotonic_anchor WHERE id=1").fetchone()

    def close(self) -> None:
        with self._lock:
            self._db.close()
