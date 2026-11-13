"""Crash-recoverable SQLite journal for signed runtime attestations and reservations.

The HMAC key must be supplied by an external secret manager. This journal detects
record tampering and reordering, but does not prevent rollback of the entire DB:
a production monotonic witness outside the SQLite rollback domain is still needed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from .contracts import Attestation
from .state import JournalEntry, StateJournal, StepReservation


ZERO_MAC = "0" * 64
SCHEMA_VERSION = 1


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: object) -> bytes:
    if not isinstance(value, str):
        raise RuntimeError("runtime_journal_invalid_binary_field")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("runtime_journal_invalid_binary_field") from exc


def _attestation_payload(item: Attestation) -> dict[str, Any]:
    return {
        "execution_id": item.execution_id,
        "principal_id": item.principal_id,
        "step_id": item.step_id,
        "agent_id": item.agent_id,
        "agent_key_fingerprint": item.agent_key_fingerprint,
        "action_digest": item.action_digest,
        "output_digest": item.output_digest,
        "verified": item.verified,
        "detail": item.detail,
        "signature": _b64(item.signature),
        "previous_attestation_digest": item.previous_attestation_digest,
        "runtime_id": item.runtime_id,
        "provenance_digest": item.provenance_digest,
        "provenance_seal": _b64(item.provenance_seal),
    }


def _attestation_from_payload(value: object) -> Attestation:
    if not isinstance(value, dict):
        raise RuntimeError("runtime_journal_invalid_attestation")
    expected = {
        "execution_id", "principal_id", "step_id", "agent_id",
        "agent_key_fingerprint", "action_digest", "output_digest", "verified",
        "detail", "signature", "previous_attestation_digest", "runtime_id",
        "provenance_digest", "provenance_seal",
    }
    if set(value) != expected:
        raise RuntimeError("runtime_journal_attestation_schema_mismatch")
    data = dict(value)
    data["signature"] = _unb64(data["signature"])
    data["provenance_seal"] = _unb64(data["provenance_seal"])
    try:
        return Attestation(**data)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("runtime_journal_invalid_attestation") from exc


class SQLiteStateJournal(StateJournal):
    """Persistent runtime journal; preserves StateJournal signature and identity checks."""

    def __init__(
        self,
        path: str,
        *,
        integrity_key: bytes,
        key_id: str,
        verifier,
        identity_registry=None,
        runtime_id: str | None = None,
    ) -> None:
        if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
            raise ValueError("absolute_runtime_journal_path_required")
        if os.path.islink(path):
            raise ValueError("runtime_journal_symlink_rejected")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("runtime_journal_integrity_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("invalid_runtime_journal_key_id")
        super().__init__(
            require_signatures=True,
            verifier=verifier,
            identity_registry=identity_registry,
            runtime_id=runtime_id,
        )
        self.path = path
        self._integrity_key = bytes(integrity_key)
        self._key_id = key_id
        self._storage_lock = RLock()
        self._failed = False
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=30000")
        self._db.execute("PRAGMA trusted_schema=OFF")
        self._db.execute("PRAGMA secure_delete=ON")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS runtime_journal_meta ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS runtime_journal_events ("
            "sequence INTEGER PRIMARY KEY, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "payload_digest TEXT NOT NULL, previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, "
            "key_id TEXT NOT NULL)"
        )
        self._initialize_metadata()
        self._head_sequence = 0
        self._head_mac = ZERO_MAC
        self._recover()
        if os.name == "posix":
            os.chmod(path, 0o600)

    @property
    def durable(self) -> bool:
        return not self._failed

    def _initialize_metadata(self) -> None:
        rows = dict(self._db.execute("SELECT key,value FROM runtime_journal_meta").fetchall())
        if not rows:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute(
                    "INSERT INTO runtime_journal_meta(key,value) VALUES('schema_version',?)",
                    (str(SCHEMA_VERSION),),
                )
                self._db.execute(
                    "INSERT INTO runtime_journal_meta(key,value) VALUES('key_id',?)",
                    (self._key_id,),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
            return
        if rows.get("schema_version") != str(SCHEMA_VERSION):
            raise RuntimeError("unsupported_runtime_journal_schema")
        if rows.get("key_id") != self._key_id:
            raise RuntimeError("runtime_journal_key_id_mismatch")

    def _mac(self, sequence: int, previous_mac: str, digest: str) -> str:
        statement = _canonical({
            "domain": "NORYX7_RUNTIME_JOURNAL_V1",
            "sequence": sequence,
            "previous_mac": previous_mac,
            "payload_digest": digest,
            "key_id": self._key_id,
        }).encode("utf-8")
        return hmac.new(self._integrity_key, statement, hashlib.sha256).hexdigest()

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT sequence,event_type,payload_json,payload_digest,previous_mac,record_mac,key_id "
            "FROM runtime_journal_events ORDER BY sequence"
        ).fetchall()
        attestations: dict[tuple[str, str], Attestation] = {}
        expected_sequence = 1
        previous_mac = ZERO_MAC
        for sequence, event_type, payload_json, digest, previous, mac, key_id in rows:
            if sequence != expected_sequence or previous != previous_mac or key_id != self._key_id:
                raise RuntimeError("runtime_journal_chain_discontinuity")
            actual_digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(actual_digest, digest):
                raise RuntimeError("runtime_journal_payload_digest_mismatch")
            if not hmac.compare_digest(self._mac(sequence, previous, digest), mac):
                raise RuntimeError("runtime_journal_authentication_failure")
            try:
                payload = json.loads(payload_json)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("runtime_journal_invalid_payload") from exc
            self._replay_event(event_type, payload, attestations)
            previous_mac = mac
            expected_sequence += 1
        self._head_sequence = expected_sequence - 1
        self._head_mac = previous_mac

    def _replay_event(self, event_type: str, payload: object, attestations: dict) -> None:
        if not isinstance(payload, dict):
            raise RuntimeError("runtime_journal_invalid_event_payload")
        if event_type == "reserve":
            if set(payload) != {"execution_id", "principal_id", "step_id", "action_digest"}:
                raise RuntimeError("runtime_journal_reservation_schema_mismatch")
            super().restore_reservation(StepReservation(**payload))
            return
        if event_type in {"append", "rollback"}:
            attestation = _attestation_from_payload(payload)
            key = (attestation.execution_id, attestation.step_id)
            if event_type == "append":
                super().append(attestation)
                attestations[key] = attestation
            else:
                prior = attestations.get(key)
                if prior is None or prior != attestation:
                    raise RuntimeError("runtime_journal_rollback_without_append")
                super().rollback_last(attestation)
                attestations.pop(key, None)
            return
        raise RuntimeError("runtime_journal_unknown_event_type")

    def _ensure_healthy(self) -> None:
        if self._failed:
            raise RuntimeError("runtime_journal_storage_failed_closed")

    def _persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._storage_lock:
            self._ensure_healthy()
            payload_json = _canonical(payload)
            digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            sequence = self._head_sequence + 1
            mac = self._mac(sequence, self._head_mac, digest)
            try:
                self._db.execute("BEGIN IMMEDIATE")
                latest = self._db.execute(
                    "SELECT sequence,record_mac FROM runtime_journal_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                actual_head = (0, ZERO_MAC) if latest is None else (latest[0], latest[1])
                if actual_head != (self._head_sequence, self._head_mac):
                    raise RuntimeError("runtime_journal_concurrent_writer_detected")
                self._db.execute(
                    "INSERT INTO runtime_journal_events VALUES(?,?,?,?,?,?,?)",
                    (sequence, event_type, payload_json, digest, self._head_mac, mac, self._key_id),
                )
                self._db.execute("COMMIT")
                self._head_sequence = sequence
                self._head_mac = mac
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                self._failed = True
                raise

    def reserve_step(self, execution_id: str, principal_id: str, step_id: str, action_digest: str) -> StepReservation:
        self._ensure_healthy()
        reservation = super().reserve_step(execution_id, principal_id, step_id, action_digest)
        try:
            self._persist_event("reserve", {
                "execution_id": reservation.execution_id,
                "principal_id": reservation.principal_id,
                "step_id": reservation.step_id,
                "action_digest": reservation.action_digest,
            })
        except Exception:
            self._failed = True
            raise
        return reservation

    def append(self, attestation: Attestation) -> JournalEntry:
        self._ensure_healthy()
        entry = super().append(attestation)
        try:
            self._persist_event("append", _attestation_payload(attestation))
        except Exception:
            self._failed = True
            raise
        return entry

    def rollback_last(self, attestation: Attestation) -> None:
        self._ensure_healthy()
        super().rollback_last(attestation)
        try:
            self._persist_event("rollback", _attestation_payload(attestation))
        except Exception:
            self._failed = True
            raise

    def snapshot(self) -> tuple[JournalEntry, ...]:
        self._ensure_healthy()
        return super().snapshot()

    def close(self) -> None:
        with self._storage_lock:
            if not self._db:
                return
            self._db.close()
            self._db = None
            self._failed = True
