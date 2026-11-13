"""Crash-recoverable runtime execution journal.

The integrity key must be supplied by an external secret store/KMS/HSM.
This journal detects tampering, reordering and interior deletion. A complete
snapshot rollback still requires an external monotonic anchor.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
from pathlib import Path
from typing import Any

from core.identity import IdentityRegistry
from .contracts import Attestation
from .state import StateJournal, StepReservation, JournalEntry, AttestationVerifier


class DurableStateJournal(StateJournal):
    """SQLite-backed runtime journal; pending reservations survive process restart."""

    SCHEMA_VERSION = 1
    _DOMAIN = b"NORYX7.RUNTIME.JOURNAL.EVENT.v1\x00"

    def __init__(
        self,
        path: str,
        *,
        integrity_key: bytes,
        key_id: str,
        require_signatures: bool = True,
        verifier: AttestationVerifier | None = None,
        identity_registry: IdentityRegistry | None = None,
        runtime_id: str | None = None,
    ) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("journal_path_required")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("integrity_key_must_be_at_least_32_bytes")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("journal_key_id_required")
        super().__init__(
            require_signatures=require_signatures,
            verifier=verifier,
            identity_registry=identity_registry,
            runtime_id=runtime_id,
        )
        self.path = str(Path(path))
        self.key_id = key_id
        self._integrity_key = bytes(integrity_key)
        self._db = sqlite3.connect(
            self.path, timeout=30, isolation_level=None, check_same_thread=False
        )
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS runtime_events ("
                "sequence INTEGER PRIMARY KEY, event_json TEXT NOT NULL, "
                "previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, "
                "key_id TEXT NOT NULL, schema_version INTEGER NOT NULL)"
            )
            self._recover()
        except Exception:
            self._db.close()
            raise

    @staticmethod
    def _canonical(value: dict[str, Any]) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )

    def _mac(self, sequence: int, previous_mac: str, event_json: str) -> str:
        message = (
            self._DOMAIN
            + str(sequence).encode("ascii") + b"\x00"
            + previous_mac.encode("ascii") + b"\x00"
            + self.key_id.encode("utf-8") + b"\x00"
            + event_json.encode("utf-8")
        )
        return hmac.new(self._integrity_key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def _reservation_payload(value: StepReservation) -> dict[str, str]:
        return {
            "execution_id": value.execution_id,
            "principal_id": value.principal_id,
            "step_id": value.step_id,
            "action_digest": value.action_digest,
        }

    @staticmethod
    def _attestation_payload(value: Attestation) -> dict[str, Any]:
        return {
            "execution_id": value.execution_id,
            "principal_id": value.principal_id,
            "step_id": value.step_id,
            "agent_id": value.agent_id,
            "agent_key_fingerprint": value.agent_key_fingerprint,
            "action_digest": value.action_digest,
            "output_digest": value.output_digest,
            "verified": value.verified,
            "detail": value.detail,
            "signature": base64.b64encode(value.signature).decode("ascii"),
            "previous_attestation_digest": value.previous_attestation_digest,
            "runtime_id": value.runtime_id,
            "provenance_digest": value.provenance_digest,
            "provenance_seal": base64.b64encode(value.provenance_seal).decode("ascii"),
        }

    @staticmethod
    def _attestation_from_payload(value: dict[str, Any]) -> Attestation:
        expected = {
            "execution_id", "principal_id", "step_id", "agent_id",
            "agent_key_fingerprint", "action_digest", "output_digest",
            "verified", "detail", "signature", "previous_attestation_digest",
            "runtime_id", "provenance_digest", "provenance_seal",
        }
        if set(value) != expected:
            raise RuntimeError("runtime_journal_attestation_schema_invalid")
        try:
            signature = base64.b64decode(value["signature"], validate=True)
            seal = base64.b64decode(value["provenance_seal"], validate=True)
        except Exception as exc:
            raise RuntimeError("runtime_journal_binary_field_invalid") from exc
        if not isinstance(value["verified"], bool):
            raise RuntimeError("runtime_journal_boolean_invalid")
        return Attestation(
            execution_id=value["execution_id"],
            principal_id=value["principal_id"],
            step_id=value["step_id"],
            agent_id=value["agent_id"],
            agent_key_fingerprint=value["agent_key_fingerprint"],
            action_digest=value["action_digest"],
            output_digest=value["output_digest"],
            verified=value["verified"],
            detail=value["detail"],
            signature=signature,
            previous_attestation_digest=value["previous_attestation_digest"],
            runtime_id=value["runtime_id"],
            provenance_digest=value["provenance_digest"],
            provenance_seal=seal,
        )

    def _persist(self, event: dict[str, Any]) -> None:
        event_json = self._canonical(event)
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT sequence, record_mac FROM runtime_events "
                    "ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if row is None else int(row[0]) + 1
                previous_mac = "0" * 64 if row is None else row[1]
                record_mac = self._mac(sequence, previous_mac, event_json)
                self._db.execute(
                    "INSERT INTO runtime_events VALUES (?,?,?,?,?,?)",
                    (sequence, event_json, previous_mac, record_mac,
                     self.key_id, self.SCHEMA_VERSION),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT sequence,event_json,previous_mac,record_mac,key_id,schema_version "
            "FROM runtime_events ORDER BY sequence"
        ).fetchall()
        expected_sequence = 1
        previous_mac = "0" * 64
        for sequence, event_json, stored_previous, stored_mac, key_id, schema in rows:
            if sequence != expected_sequence:
                raise RuntimeError("runtime_journal_sequence_gap")
            if schema != self.SCHEMA_VERSION or key_id != self.key_id:
                raise RuntimeError("runtime_journal_schema_or_key_mismatch")
            if stored_previous != previous_mac:
                raise RuntimeError("runtime_journal_chain_discontinuity")
            expected_mac = self._mac(sequence, previous_mac, event_json)
            if not hmac.compare_digest(stored_mac, expected_mac):
                raise RuntimeError("runtime_journal_integrity_failure")
            try:
                event = json.loads(event_json)
            except Exception as exc:
                raise RuntimeError("runtime_journal_event_invalid") from exc
            if not isinstance(event, dict) or set(event) != {"type", "payload"}:
                raise RuntimeError("runtime_journal_event_schema_invalid")
            payload = event["payload"]
            if event["type"] == "reservation":
                if not isinstance(payload, dict) or set(payload) != {
                    "execution_id", "principal_id", "step_id", "action_digest"
                }:
                    raise RuntimeError("runtime_journal_reservation_schema_invalid")
                super().restore_reservation(StepReservation(**payload))
            elif event["type"] == "attestation":
                if not isinstance(payload, dict):
                    raise RuntimeError("runtime_journal_attestation_schema_invalid")
                super().append(self._attestation_from_payload(payload))
            else:
                raise RuntimeError("runtime_journal_event_type_invalid")
            previous_mac = stored_mac
            expected_sequence += 1

    def reserve_step(
        self, execution_id: str, principal_id: str, step_id: str, action_digest: str
    ) -> StepReservation:
        reservation = super().reserve_step(
            execution_id, principal_id, step_id, action_digest
        )
        try:
            self._persist({
                "type": "reservation",
                "payload": self._reservation_payload(reservation),
            })
        except Exception:
            # Keep the in-memory reservation: refusing dispatch is safer than
            # reopening the step after a persistence failure.
            raise
        return reservation

    def restore_reservation(self, reservation: StepReservation) -> None:
        super().restore_reservation(reservation)
        self._persist({
            "type": "reservation",
            "payload": self._reservation_payload(reservation),
        })

    def append(self, attestation: Attestation) -> JournalEntry:
        entry = super().append(attestation)
        try:
            self._persist({
                "type": "attestation",
                "payload": self._attestation_payload(attestation),
            })
        except Exception:
            # Restore the pre-dispatch block if durable commit fails.
            super().rollback_last(attestation)
            raise
        return entry

    def rollback_last(self, attestation: Attestation) -> None:
        raise RuntimeError("durable_runtime_journal_is_append_only")

    def close(self) -> None:
        with self._lock:
            self._db.close()
