from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any


class DurableAttestationStore:
    """SQLite-backed append-only persistence for attestations and reconciliation events."""

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path:
            raise ValueError("persistence path must be a non-empty string")
        self.path = str(Path(path).expanduser())
        parent = Path(self.path).parent
        parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                sequence INTEGER PRIMARY KEY,
                payload TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS commit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY(journal_sequence) REFERENCES journal_entries(sequence)
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(execution_id, step_id)
            )
        """)

    @staticmethod
    def _encode(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def load(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        entries = [json.loads(row[0]) for row in self._db.execute("SELECT payload FROM journal_entries ORDER BY sequence")]
        events = [json.loads(row[0]) for row in self._db.execute("SELECT payload FROM commit_events ORDER BY id")]
        reservations = [json.loads(row[0]) for row in self._db.execute("SELECT payload FROM reservations ORDER BY execution_id, step_id")]
        return entries, events, reservations

    def append_entry(self, payload: dict[str, Any]) -> None:
        sequence = int(payload["sequence"])
        self._db.execute("INSERT INTO journal_entries(sequence,payload) VALUES(?,?)", (sequence, self._encode(payload)))

    def append_event(self, payload: dict[str, Any]) -> None:
        sequence = int(payload["journal_sequence"])
        self._db.execute("INSERT INTO commit_events(journal_sequence,payload) VALUES(?,?)", (sequence, self._encode(payload)))

    def put_reservation(self, payload: dict[str, Any]) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO reservations(execution_id,step_id,payload) VALUES(?,?,?)",
            (payload["execution_id"], payload["step_id"], self._encode(payload)),
        )

    def delete_reservation(self, execution_id: str, step_id: str) -> None:
        self._db.execute("DELETE FROM reservations WHERE execution_id=? AND step_id=?", (execution_id, step_id))

    def close(self) -> None:
        self._db.close()
