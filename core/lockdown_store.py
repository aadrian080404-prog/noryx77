"""Transactional persistence for the authenticated NORYX7 lockdown continuity seal."""

from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from threading import Lock


class SQLiteLockdownStore:
    """Persist the latest authenticated lockdown seal across runtime/process restarts.

    The database records the highest accepted generation and refuses rollback. The
    cryptographic seal remains authoritative for authenticity; the database provides
    cross-process continuity, monotonic rollback detection, and compare-and-swap
    protection against two runtimes committing different states from the same base.
    """

    def __init__(self, path: str | Path):
        if not isinstance(path, (str, Path)) or not str(path).strip():
            raise ValueError("invalid_lockdown_store_path")
        self.path = str(path)
        self._lock = Lock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS lockdown_state (id INTEGER PRIMARY KEY CHECK (id = 1), generation INTEGER NOT NULL, seal TEXT NOT NULL)"
            )

    @staticmethod
    def _encode(seal: dict) -> str:
        def encode(value):
            if isinstance(value, bytes):
                return {"__bytes__": base64.b64encode(value).decode("ascii")}
            raise TypeError("invalid_lockdown_seal_value")

        return json.dumps(seal, sort_keys=True, separators=(",", ":"), default=encode)

    @staticmethod
    def _decode(value: str) -> dict:
        def decode(item):
            if isinstance(item, dict) and set(item) == {"__bytes__"}:
                return base64.b64decode(item["__bytes__"], validate=True)
            return item

        result = json.loads(value, object_hook=decode)
        if not isinstance(result, dict):
            raise ValueError("invalid_persisted_lockdown_seal")
        return result

    @staticmethod
    def _generation(seal: dict) -> int:
        payload = seal.get("payload")
        if not isinstance(payload, bytes):
            raise ValueError("invalid_persisted_lockdown_seal")
        data = json.loads(payload.decode("utf-8"))
        generation = data.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("invalid_persisted_lockdown_seal")
        return generation

    def load(self) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT seal FROM lockdown_state WHERE id = 1").fetchone()
            if row is None:
                return None
            return self._decode(row[0])

    def save(self, seal: dict, *, expected_generation: int | None = None) -> None:
        generation = self._generation(seal)
        if expected_generation is not None and (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or expected_generation < 0
        ):
            raise ValueError("invalid_expected_generation")
        encoded = self._encode(seal)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT generation FROM lockdown_state WHERE id = 1").fetchone()
            if expected_generation is not None:
                if row is None or row[0] != expected_generation:
                    raise ValueError("lockdown_store_conflict")
            elif row is not None and generation < row[0]:
                raise ValueError("lockdown_store_rollback")
            connection.execute(
                "INSERT INTO lockdown_state(id, generation, seal) VALUES(1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET generation=excluded.generation, seal=excluded.seal",
                (generation, encoded),
            )
            connection.commit()
