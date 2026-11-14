"""Crash-durable SQLite implementation of the NORYX7 audit-chain contract."""
from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac

from .audit import AuditCheckpoint, AuditLog
from .crypto import KeyProvider


class SQLiteAuditLog(AuditLog):
    """Append-only, multi-process audit chain backed by SQLite WAL.

    Each append obtains a write transaction before reading the chain tip, so
    concurrent writers serialize and cannot fork the local chain. FULL
    synchronous commits are used; external checkpoints remain necessary to
    detect replacement of the entire database by an older valid copy.
    """

    def __init__(self, path: str, *, busy_timeout_ms: int = 5000) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("audit_database_path_required")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or not 1 <= busy_timeout_ms <= 60000:
            raise ValueError("audit_busy_timeout_invalid")
        self.path = str(Path(path).expanduser())
        self._busy_timeout_ms = busy_timeout_ms
        self._closed = False
        self._db_lock = RLock()
        super().__init__()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    digest TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS audit_events_digest_idx ON audit_events(digest)"
            )
        self._reload_cache()

    def _connect(self):
        if self._closed:
            raise RuntimeError("audit_log_closed")
        connection = sqlite3.connect(
            self.path, timeout=self._busy_timeout_ms / 1000, isolation_level=None
        )
        connection.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA trusted_schema=OFF")
        return connection

    @staticmethod
    def _decode_rows(rows) -> tuple[dict[str, Any], ...]:
        decoded = []
        for raw in rows:
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError("audit_record_not_object")
            decoded.append(item)
        return tuple(decoded)

    def _reload_cache(self) -> None:
        rows = self.snapshot()
        digests = []
        with self._connect() as connection:
            digests = [row[0] for row in connection.execute(
                "SELECT digest FROM audit_events ORDER BY sequence"
            )]
        with self._db_lock:
            self._events = [deepcopy(item) for item in rows]
            self._digests = list(digests)

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        entry = deepcopy({"event": event, **data})
        try:
            encoded = json.dumps(
                entry, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("audit data must be JSON serializable") from exc
        with self._db_lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    row = connection.execute(
                        "SELECT digest FROM audit_events ORDER BY sequence DESC LIMIT 1"
                    ).fetchone()
                    previous = row[0] if row else self._GENESIS
                    digest = self._digest(entry, previous)
                    connection.execute(
                        "INSERT INTO audit_events(event_json, digest) VALUES (?, ?)",
                        (encoded, digest),
                    )
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
            self._reload_cache()
        return deepcopy(entry)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_json FROM audit_events ORDER BY sequence"
            ).fetchall()
        return self._decode_rows(row[0] for row in rows)

    def _rows(self):
        with self._connect() as connection:
            return connection.execute(
                "SELECT sequence, event_json, digest FROM audit_events ORDER BY sequence"
            ).fetchall()

    def _verify_integrity_locked(self) -> bool:
        try:
            rows = self._rows()
            previous = self._GENESIS
            for expected_sequence, (sequence, raw, digest) in enumerate(rows, 1):
                if sequence != expected_sequence:
                    return False
                entry = json.loads(raw)
                if not isinstance(entry, dict) or not isinstance(digest, str):
                    return False
                if self._digest(entry, previous) != digest:
                    return False
                previous = digest
            return True
        except Exception:
            return False

    def verify_integrity(self) -> bool:
        with self._db_lock:
            return self._verify_integrity_locked()

    def digest(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT digest FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else self._GENESIS

    def checkpoint(self, provider: KeyProvider, *, key_id: str) -> AuditCheckpoint:
        if not isinstance(provider, KeyProvider):
            raise ValueError("key_provider_required")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        with self._db_lock:
            if not self._verify_integrity_locked():
                raise ValueError("audit_integrity_failed")
            current_digest = self.digest()
        try:
            key = provider.get_key(key_id)
        except Exception as exc:
            raise ValueError("audit_checkpoint_key_unavailable") from exc
        if not isinstance(key, bytes) or not key:
            raise ValueError("audit_checkpoint_key_required")
        signer = hmac.HMAC(key, hashes.SHA256())
        signer.update(self._checkpoint_payload(current_digest))
        return AuditCheckpoint(1, key_id, current_digest, signer.finalize())

    def verify_checkpoint(self, checkpoint: AuditCheckpoint, provider: KeyProvider) -> bool:
        if not isinstance(provider, KeyProvider) or not isinstance(checkpoint, AuditCheckpoint):
            return False
        with self._db_lock:
            current_digest = self.digest()
            if not checkpoint.is_well_formed() or checkpoint.digest != current_digest or not self._verify_integrity_locked():
                return False
        try:
            key = provider.get_key(checkpoint.key_id)
            if not isinstance(key, bytes) or not key:
                return False
            verifier = hmac.HMAC(key, hashes.SHA256())
            verifier.update(self._checkpoint_payload(checkpoint.digest))
            verifier.verify(checkpoint.mac)
            with self._db_lock:
                return self.digest() == current_digest and self._verify_integrity_locked()
        except (Exception, InvalidSignature):
            return False

    def close(self) -> None:
        with self._db_lock:
            self._closed = True
