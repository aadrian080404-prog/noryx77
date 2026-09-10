from __future__ import annotations

import sqlite3
from pathlib import Path


class DurableDispatchEvidenceStore:
    """Durable evidence that a dispatch started and, when available, returned."""

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path:
            raise ValueError("persistence path must be a non-empty string")
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                action_digest TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                output_digest TEXT NOT NULL,
                UNIQUE(execution_id, step_id)
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                action_digest TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                output_digest TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS dispatch_events_started_once
            ON dispatch_events(execution_id, step_id)
            WHERE outcome = 'started'
        """)

    def append_started(self, *, execution_id: str, principal_id: str, step_id: str,
                       action_digest: str, agent_id: str, runtime_id: str) -> None:
        try:
            self._db.execute(
                "INSERT INTO dispatch_events(execution_id,principal_id,step_id,action_digest,agent_id,runtime_id,outcome,output_digest) VALUES(?,?,?,?,?,?,?,?)",
                (execution_id, principal_id, step_id, action_digest, agent_id, runtime_id, "started", ""),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate dispatch start evidence") from exc

    def append_returned(self, *, execution_id: str, principal_id: str, step_id: str,
                        action_digest: str, agent_id: str, runtime_id: str,
                        output_digest: str) -> None:
        try:
            self._db.execute("BEGIN IMMEDIATE")
            started = self._db.execute(
                "SELECT principal_id,action_digest,agent_id,runtime_id FROM dispatch_events WHERE execution_id=? AND step_id=? AND outcome='started'",
                (execution_id, step_id),
            ).fetchone()
            if started is None:
                self._db.execute("ROLLBACK")
                raise ValueError("dispatch start evidence missing")
            if started != (principal_id, action_digest, agent_id, runtime_id):
                self._db.execute("ROLLBACK")
                raise ValueError("dispatch start evidence mismatch")
            self._db.execute(
                "INSERT INTO dispatch_evidence(execution_id,principal_id,step_id,action_digest,agent_id,runtime_id,outcome,output_digest) VALUES(?,?,?,?,?,?,?,?)",
                (execution_id, principal_id, step_id, action_digest, agent_id, runtime_id, "returned", output_digest),
            )
            self._db.execute(
                "INSERT INTO dispatch_events(execution_id,principal_id,step_id,action_digest,agent_id,runtime_id,outcome,output_digest) VALUES(?,?,?,?,?,?,?,?)",
                (execution_id, principal_id, step_id, action_digest, agent_id, runtime_id, "returned", output_digest),
            )
            self._db.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            self._db.execute("ROLLBACK")
            raise ValueError("duplicate dispatch evidence") from exc
        except Exception:
            try:
                self._db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

    def close(self) -> None:
        self._db.close()
