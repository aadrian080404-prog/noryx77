from __future__ import annotations

import sqlite3
from pathlib import Path


class DurableDispatchEvidenceStore:
    """Durable append-only evidence that an execution dispatch returned."""

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path:
            raise ValueError("persistence path must be a non-empty string")
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
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

    def append_returned(self, *, execution_id: str, principal_id: str, step_id: str,
                        action_digest: str, agent_id: str, runtime_id: str,
                        output_digest: str) -> None:
        try:
            self._db.execute(
                "INSERT INTO dispatch_evidence(execution_id,principal_id,step_id,action_digest,agent_id,runtime_id,outcome,output_digest) VALUES(?,?,?,?,?,?,?,?)",
                (execution_id, principal_id, step_id, action_digest, agent_id, runtime_id, "returned", output_digest),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate dispatch evidence") from exc

    def close(self) -> None:
        self._db.close()
