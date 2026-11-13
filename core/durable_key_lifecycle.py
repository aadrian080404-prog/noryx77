"""Persistent metadata state machine for external KMS/HSM keys.

Raw key material is never stored here. Integrity keys must be supplied from a
separate secret boundary. Full database rollback needs an external witness.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3

from core.key_lifecycle import KeyLifecycle, KeyRecord, KeyState


class DurableKeyLifecycle(KeyLifecycle):
    SCHEMA_VERSION = 1
    _DOMAIN = b"NORYX7.KEY.LIFECYCLE.EVENT.v1\x00"

    def __init__(self, path: str, *, integrity_key: bytes, key_id: str) -> None:
        if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
            raise ValueError("absolute_key_lifecycle_path_required")
        if os.path.islink(path):
            raise ValueError("key_lifecycle_symlink_rejected")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("key_lifecycle_integrity_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("key_lifecycle_key_id_required")
        super().__init__()
        self.path = path
        self._integrity_key = bytes(integrity_key)
        self._integrity_key_id = key_id
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._closed = False
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS key_lifecycle_events ("
                "sequence INTEGER PRIMARY KEY, event_json TEXT NOT NULL, "
                "previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, "
                "key_id TEXT NOT NULL, schema_version INTEGER NOT NULL)"
            )
            self._recover()
            if os.name == "posix":
                for candidate in (path, path + "-wal", path + "-shm"):
                    if os.path.exists(candidate) and not os.path.islink(candidate):
                        os.chmod(candidate, 0o600)
        except Exception:
            self._db.close()
            self._closed = True
            raise

    @staticmethod
    def _canonical(event: dict) -> str:
        return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    def _mac(self, sequence: int, previous_mac: str, raw: str) -> str:
        message = (
            self._DOMAIN + str(sequence).encode("ascii") + b"\x00"
            + previous_mac.encode("ascii") + b"\x00"
            + self._integrity_key_id.encode("utf-8") + b"\x00"
            + raw.encode("utf-8")
        )
        return hmac.new(self._integrity_key, message, hashlib.sha256).hexdigest()

    def _append(self, event: dict) -> None:
        if self._closed:
            raise RuntimeError("key_lifecycle_closed")
        raw = self._canonical(event)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            row = self._db.execute(
                "SELECT sequence,record_mac FROM key_lifecycle_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if row is None else int(row[0]) + 1
            previous = "0" * 64 if row is None else row[1]
            mac = self._mac(sequence, previous, raw)
            self._db.execute(
                "INSERT INTO key_lifecycle_events VALUES(?,?,?,?,?,?)",
                (sequence, raw, previous, mac, self._integrity_key_id, self.SCHEMA_VERSION),
            )
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT sequence,event_json,previous_mac,record_mac,key_id,schema_version "
            "FROM key_lifecycle_events ORDER BY sequence"
        ).fetchall()
        expected, previous = 1, "0" * 64
        for sequence, raw, stored_previous, stored_mac, key_id, schema in rows:
            if sequence != expected:
                raise RuntimeError("key_lifecycle_sequence_gap")
            if key_id != self._integrity_key_id or schema != self.SCHEMA_VERSION:
                raise RuntimeError("key_lifecycle_schema_or_key_mismatch")
            if stored_previous != previous:
                raise RuntimeError("key_lifecycle_chain_discontinuity")
            if not hmac.compare_digest(stored_mac, self._mac(sequence, previous, raw)):
                raise RuntimeError("key_lifecycle_integrity_failure")
            try:
                event = json.loads(raw)
            except Exception as exc:
                raise RuntimeError("key_lifecycle_event_invalid") from exc
            if not isinstance(event, dict) or set(event) != {"operation", "key_id", "version", "state"}:
                raise RuntimeError("key_lifecycle_event_schema_invalid")
            name, version, state = event["key_id"], event["version"], event["state"]
            if not isinstance(name, str) or not name.strip():
                raise RuntimeError("key_lifecycle_key_name_invalid")
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise RuntimeError("key_lifecycle_version_invalid")
            try:
                if event["operation"] == "register":
                    record = super().register(name, version=version)
                elif event["operation"] == "rotate":
                    record = super().rotate(name)
                elif event["operation"] == "retire":
                    record = super().retire(name)
                elif event["operation"] == "revoke":
                    record = super().revoke(name)
                else:
                    raise RuntimeError("key_lifecycle_operation_invalid")
            except Exception as exc:
                raise RuntimeError("key_lifecycle_replay_rejected") from exc
            if record.version != version or record.state.value != state:
                raise RuntimeError("key_lifecycle_replay_state_mismatch")
            previous, expected = stored_mac, expected + 1

    @property
    def durable(self) -> bool:
        return not self._closed

    def register(self, key_id: str, *, version: int = 1) -> KeyRecord:
        with self._lock:
            if not isinstance(key_id, str) or not key_id.strip():
                raise ValueError("invalid_key_id")
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise ValueError("invalid_key_version")
            if key_id in self._records:
                raise ValueError("key_id_already_registered")
            self._append({"operation": "register", "key_id": key_id, "version": version, "state": KeyState.ACTIVE.value})
            return super().register(key_id, version=version)

    def rotate(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            if current.state is KeyState.REVOKED:
                raise PermissionError("revoked_key_cannot_rotate")
            if current.state is KeyState.RETIRING:
                raise PermissionError("retiring_key_cannot_reactivate")
            version = current.version + 1
            self._append({"operation": "rotate", "key_id": key_id, "version": version, "state": KeyState.ACTIVE.value})
            return super().rotate(key_id)

    def retire(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            if current.state is KeyState.REVOKED:
                raise PermissionError("revoked_key_cannot_retire")
            self._append({"operation": "retire", "key_id": key_id, "version": current.version, "state": KeyState.RETIRING.value})
            return super().retire(key_id)

    def revoke(self, key_id: str) -> KeyRecord:
        with self._lock:
            current = self._records.get(key_id)
            if current is None:
                raise KeyError("unknown_key_id")
            self._append({"operation": "revoke", "key_id": key_id, "version": current.version, "state": KeyState.REVOKED.value})
            return super().revoke(key_id)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
