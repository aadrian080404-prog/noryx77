"""Authenticated persistent security event stream.

Event evidence remains a digest/reference; this bus does not store sensitive
payloads. The HMAC key must be provisioned outside the database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from math import isfinite

from core.observability import EventKind, ObservedEvent, SecurityEventBus


class DurableSecurityEventBus(SecurityEventBus):
    SCHEMA_VERSION = 1
    _DOMAIN = b"NORYX7.SECURITY.EVENT.v1\x00"

    def __init__(self, path: str, *, integrity_key: bytes, key_id: str, max_events: int = 65_536) -> None:
        if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
            raise ValueError("absolute_security_event_path_required")
        if os.path.islink(path):
            raise ValueError("security_event_symlink_rejected")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("security_event_integrity_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("security_event_key_id_required")
        super().__init__(max_events=max_events)
        self.path = path
        self._integrity_key = bytes(integrity_key)
        self._key_id = key_id
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._failed = False
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS security_events ("
                "sequence INTEGER PRIMARY KEY, event_json TEXT NOT NULL, "
                "previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, "
                "key_id TEXT NOT NULL, schema_version INTEGER NOT NULL)"
            )
            self._recover()
            self._secure_permissions()
        except Exception:
            self._db.close()
            self._failed = True
            raise

    @staticmethod
    def _canonical(event: dict) -> str:
        return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    def _mac(self, sequence: int, previous_mac: str, raw: str) -> str:
        message = (
            self._DOMAIN + str(sequence).encode("ascii") + b"\x00"
            + previous_mac.encode("ascii") + b"\x00"
            + self._key_id.encode("utf-8") + b"\x00"
            + raw.encode("utf-8")
        )
        return hmac.new(self._integrity_key, message, hashlib.sha256).hexdigest()

    def _secure_permissions(self) -> None:
        if os.name == "posix":
            for candidate in (self.path, self.path + "-wal", self.path + "-shm"):
                if os.path.exists(candidate) and not os.path.islink(candidate):
                    os.chmod(candidate, 0o600)

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT sequence,event_json,previous_mac,record_mac,key_id,schema_version "
            "FROM security_events ORDER BY sequence"
        ).fetchall()
        expected, previous = 1, "0" * 64
        for sequence, raw, stored_previous, stored_mac, key_id, schema in rows:
            if sequence != expected:
                raise RuntimeError("security_event_sequence_gap")
            if key_id != self._key_id or schema != self.SCHEMA_VERSION:
                raise RuntimeError("security_event_schema_or_key_mismatch")
            if stored_previous != previous:
                raise RuntimeError("security_event_chain_discontinuity")
            if not hmac.compare_digest(stored_mac, self._mac(sequence, previous, raw)):
                raise RuntimeError("security_event_integrity_failure")
            try:
                event = json.loads(raw)
                if not isinstance(event, dict) or set(event) != {
                    "kind", "component", "severity", "timestamp", "evidence_digest"
                }:
                    raise ValueError("event_schema")
                kind = EventKind(event["kind"])
                component, severity = event["component"], event["severity"]
                timestamp, digest = event["timestamp"], event["evidence_digest"]
                if not isinstance(component, str) or not component.strip():
                    raise ValueError("component")
                if isinstance(severity, bool) or not isinstance(severity, int) or not 0 <= severity <= 100:
                    raise ValueError("severity")
                if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not isfinite(timestamp):
                    raise ValueError("timestamp")
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError("digest")
            except Exception as exc:
                raise RuntimeError("security_event_payload_invalid") from exc
            self._events.append(ObservedEvent(sequence, kind, component, severity, float(timestamp), digest))
            previous, expected = stored_mac, expected + 1
        if len(self._events) > self._max_events:
            raise RuntimeError("security_event_capacity_exceeded")

    @property
    def durable(self) -> bool:
        return not self._failed and self._db is not None

    def publish(self, kind: EventKind, *, component: str, severity: int, evidence_digest: str) -> ObservedEvent:
        with self._lock:
            if not self.durable:
                raise RuntimeError("security_event_bus_failed_closed")
            event = super().publish(kind, component=component, severity=severity, evidence_digest=evidence_digest)
            raw = self._canonical({
                "kind": event.kind.value,
                "component": event.component,
                "severity": event.severity,
                "timestamp": event.timestamp,
                "evidence_digest": event.evidence_digest,
            })
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT sequence,record_mac FROM security_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if row is None else int(row[0]) + 1
                if sequence != event.event_id:
                    raise RuntimeError("security_event_sequence_conflict")
                previous = "0" * 64 if row is None else row[1]
                mac = self._mac(sequence, previous, raw)
                self._db.execute(
                    "INSERT INTO security_events VALUES(?,?,?,?,?,?)",
                    (sequence, raw, previous, mac, self._key_id, self.SCHEMA_VERSION),
                )
                self._db.execute("COMMIT")
                self._secure_permissions()
                return event
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                self._events.pop()
                self._failed = True
                raise

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            self._failed = True
