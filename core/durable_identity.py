"""SQLite-backed, authenticated agent identity trust registry.

The HMAC key is supplied by the caller and must live outside this database.
A full database snapshot rollback requires an external monotonic witness.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
from pathlib import Path

from core.identity import AgentIdentity, IdentityRegistry


class DurableIdentityRegistry(IdentityRegistry):
    SCHEMA_VERSION = 1
    _DOMAIN = b"NORYX7.IDENTITY.REGISTRY.EVENT.v1\x00"

    def __init__(self, path: str, *, integrity_key: bytes, key_id: str) -> None:
        if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
            raise ValueError("absolute_identity_registry_path_required")
        if os.path.islink(path):
            raise ValueError("identity_registry_symlink_rejected")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("identity_registry_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("identity_registry_key_id_required")
        super().__init__()
        self.path = str(Path(path))
        self.key_id = key_id
        self._integrity_key = bytes(integrity_key)
        self._db = sqlite3.connect(
            self.path, timeout=30, isolation_level=None, check_same_thread=False
        )
        self._closed = False
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS identity_events ("
                "sequence INTEGER PRIMARY KEY, event_json TEXT NOT NULL, "
                "previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, "
                "key_id TEXT NOT NULL, schema_version INTEGER NOT NULL)"
            )
            self._recover()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    @staticmethod
    def _canonical(event: dict) -> str:
        return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    def _mac(self, sequence: int, previous_mac: str, event_json: str) -> str:
        payload = (
            self._DOMAIN + str(sequence).encode("ascii") + b"\x00"
            + previous_mac.encode("ascii") + b"\x00"
            + self.key_id.encode("utf-8") + b"\x00"
            + event_json.encode("utf-8")
        )
        return hmac.new(self._integrity_key, payload, hashlib.sha256).hexdigest()

    def _append_event(self, event: dict) -> None:
        event_json = self._canonical(event)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            row = self._db.execute(
                "SELECT sequence, record_mac FROM identity_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if row is None else int(row[0]) + 1
            previous = "0" * 64 if row is None else row[1]
            mac = self._mac(sequence, previous, event_json)
            self._db.execute(
                "INSERT INTO identity_events VALUES (?,?,?,?,?,?)",
                (sequence, event_json, previous, mac, self.key_id, self.SCHEMA_VERSION),
            )
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT sequence,event_json,previous_mac,record_mac,key_id,schema_version "
            "FROM identity_events ORDER BY sequence"
        ).fetchall()
        expected, previous = 1, "0" * 64
        for sequence, raw, stored_previous, stored_mac, key_id, schema in rows:
            if sequence != expected:
                raise RuntimeError("identity_registry_sequence_gap")
            if key_id != self.key_id or schema != self.SCHEMA_VERSION:
                raise RuntimeError("identity_registry_key_or_schema_mismatch")
            if stored_previous != previous:
                raise RuntimeError("identity_registry_chain_discontinuity")
            if not hmac.compare_digest(stored_mac, self._mac(sequence, previous, raw)):
                raise RuntimeError("identity_registry_integrity_failure")
            try:
                event = json.loads(raw)
            except Exception as exc:
                raise RuntimeError("identity_registry_event_invalid") from exc
            if not isinstance(event, dict) or set(event) != {"type", "agent_id", "public_key"}:
                raise RuntimeError("identity_registry_event_schema_invalid")
            agent_id, encoded_key = event["agent_id"], event["public_key"]
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RuntimeError("identity_registry_agent_id_invalid")
            if event["type"] == "register":
                import base64
                try:
                    public_key = base64.b64decode(encoded_key, validate=True)
                except Exception as exc:
                    raise RuntimeError("identity_registry_public_key_invalid") from exc
                super().register(AgentIdentity(agent_id, public_key))
            elif event["type"] == "revoke":
                if encoded_key is not None:
                    raise RuntimeError("identity_registry_revoke_schema_invalid")
                super().revoke(agent_id)
            else:
                raise RuntimeError("identity_registry_event_type_invalid")
            previous, expected = stored_mac, expected + 1

    @property
    def durable(self) -> bool:
        return not self._closed

    def register(self, identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        with self._lock:
            if identity.agent_id in self._keys:
                raise ValueError("agent_identity_already_registered")
            import base64
            self._append_event({
                "type": "register",
                "agent_id": identity.agent_id,
                "public_key": base64.b64encode(identity.public_key).decode("ascii"),
            })
            super().register(identity)

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._append_event({
                "type": "revoke", "agent_id": agent_id, "public_key": None
            })
            super().revoke(agent_id)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
