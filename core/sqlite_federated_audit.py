"""Durable SQLite-backed hash-chain sink for federated action audit records.

This store makes audit records survive process restarts. It is tamper-evident
against accidental row edits, but a local SQLite file is not an independent
trust anchor and does not prevent whole-file rollback.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Protocol


_GENESIS = hashlib.sha256(b"noryx7/sqlite-federated-audit/genesis/v1").hexdigest()
_DOMAIN = b"noryx7/sqlite-federated-audit/event/v1/"
_MAX_AUDIT_RECORD_BYTES = 65_536


class ExternalAuditAnchor(Protocol):
    """Independently protected monotonic checkpoint service contract."""

    def read_checkpoint(self) -> tuple[int, str]:
        ...

    def compare_and_advance(
        self,
        expected_sequence: int,
        expected_digest: str,
        next_sequence: int,
        next_digest: str,
    ) -> bool:
        ...


class SQLiteFederatedAuditLog:
    """Append-only, transactionally persisted audit sink compatible with recorder."""

    def __init__(self, db_path: str | Path, *, clock=time.time) -> None:
        if str(db_path) == ":memory:":
            raise ValueError("durable_audit_database_required")
        if not callable(clock):
            raise TypeError("audit_clock_required")
        self._clock = clock
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False, isolation_level=None,
            timeout=5.0,
        )
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS federated_audit_events (
                    sequence INTEGER PRIMARY KEY,
                    event_json TEXT NOT NULL,
                    previous_digest TEXT NOT NULL,
                    digest TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS federated_audit_no_update
                BEFORE UPDATE ON federated_audit_events
                BEGIN SELECT RAISE(ABORT, 'federated_audit_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS federated_audit_no_delete
                BEFORE DELETE ON federated_audit_events
                BEGIN SELECT RAISE(ABORT, 'federated_audit_append_only'); END;
                """
            )
            if not self._verify_locked():
                self._conn.close()
                raise RuntimeError("federated_audit_integrity_failed")

    @staticmethod
    def _encode(entry: dict[str, Any]) -> str:
        try:
            encoded = json.dumps(
                entry, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            )
        except (TypeError, ValueError, UnicodeError):
            raise ValueError("audit_data_not_canonicalizable") from None
        if len(encoded.encode("utf-8")) > _MAX_AUDIT_RECORD_BYTES:
            raise ValueError("audit_record_too_large")
        return encoded

    @staticmethod
    def _event_digest(previous_digest: str, encoded: str) -> str:
        return hashlib.sha256(
            _DOMAIN + previous_digest.encode("ascii") + b"\x00"
            + encoded.encode("utf-8")
        ).hexdigest()

    def _verify_locked(self) -> bool:
        previous = _GENESIS
        expected_sequence = 1
        try:
            rows = self._conn.execute(
                "SELECT sequence, event_json, previous_digest, digest "
                "FROM federated_audit_events ORDER BY sequence"
            ).fetchall()
            for sequence, encoded, stored_previous, stored_digest in rows:
                if sequence != expected_sequence or stored_previous != previous:
                    return False
                entry = json.loads(encoded)
                if not isinstance(entry, dict):
                    return False
                canonical = self._encode(entry)
                if canonical != encoded:
                    return False
                actual = self._event_digest(previous, encoded)
                if actual != stored_digest:
                    return False
                previous = actual
                expected_sequence += 1
            return True
        except (sqlite3.Error, TypeError, ValueError, UnicodeError):
            return False

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit_event_required")
        stored = deepcopy({"event": event, **data})
        encoded = self._encode(stored)
        try:
            timestamp = self._clock()
        except Exception:
            raise RuntimeError("audit_clock_unavailable") from None
        try:
            valid_timestamp = (
                not isinstance(timestamp, bool)
                and isinstance(timestamp, (int, float))
                and math.isfinite(float(timestamp))
                and timestamp >= 0
            )
        except (OverflowError, TypeError, ValueError):
            valid_timestamp = False
        if not valid_timestamp:
            raise RuntimeError("audit_clock_invalid")
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if not self._verify_locked():
                    raise RuntimeError("federated_audit_integrity_failed")
                row = self._conn.execute(
                    "SELECT sequence, digest FROM federated_audit_events "
                    "ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if row is None else row[0] + 1
                previous = _GENESIS if row is None else row[1]
                digest = self._event_digest(previous, encoded)
                self._conn.execute(
                    "INSERT INTO federated_audit_events "
                    "(sequence, event_json, previous_digest, digest, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (sequence, encoded, previous, digest, float(timestamp)),
                )
                self._conn.execute("COMMIT")
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise
        return deepcopy(stored)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            if not self._verify_locked():
                raise RuntimeError("federated_audit_integrity_failed")
            rows = self._conn.execute(
                "SELECT event_json FROM federated_audit_events ORDER BY sequence"
            ).fetchall()
            return tuple(deepcopy(json.loads(row[0])) for row in rows)

    def verify_integrity(self) -> bool:
        with self._lock:
            return self._verify_locked()

    def checkpoint(self) -> tuple[int, str]:
        """Return a verified (sequence, digest) checkpoint for external anchoring.

        A checkpoint is never exported from a chain that fails local integrity
        verification. The tuple is a local observation, not proof against
        whole-file rollback; callers must compare it with an independent anchor.
        """
        with self._lock:
            try:
                # Keep full-chain verification and head extraction in one
                # SQLite read snapshot, even when another connection appends.
                self._conn.execute("BEGIN")
                if not self._verify_locked():
                    raise RuntimeError("federated_audit_integrity_failed")
                row = self._conn.execute(
                    "SELECT sequence, digest FROM federated_audit_events "
                    "ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                checkpoint = (0, _GENESIS) if row is None else (row[0], row[1])
                self._conn.execute("COMMIT")
                return checkpoint
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise

    def verify_against_anchor(self, anchor_sequence: int, anchor_digest: str) -> tuple[int, str]:
        """Fail closed if the local journal is behind or diverges from an anchor.

        The anchor must be read from an independently protected monotonic
        service. This method only compares observations; it does not contact,
        authenticate, or update that service. A local checkpoint ahead of the
        anchor is returned so the caller can request an anchor advance.
        """
        if (isinstance(anchor_sequence, bool)
                or not isinstance(anchor_sequence, int)
                or not 0 <= anchor_sequence <= 0x7FFFFFFFFFFFFFFF):
            raise ValueError("invalid_external_audit_checkpoint_sequence")
        if (not isinstance(anchor_digest, str)
                or len(anchor_digest) != 64
                or any(ch not in "0123456789abcdef" for ch in anchor_digest)):
            raise ValueError("invalid_external_audit_checkpoint_digest")
        local_sequence, local_digest = self.checkpoint()
        if local_sequence < anchor_sequence:
            raise RuntimeError("federated_audit_rollback_detected")
        if local_sequence == anchor_sequence and local_digest != anchor_digest:
            raise RuntimeError("federated_audit_anchor_divergence")
        return local_sequence, local_digest
    def synchronize_external_anchor(
        self, anchor: ExternalAuditAnchor
    ) -> tuple[int, str]:
        """Verify the local chain against an independent anchor and CAS-advance it.

        The anchor implementation must provide durable, monotonic storage outside
        this SQLite journal. This method defines the protocol and fail-closed
        synchronization; it does not itself provide a remote anchor service.
        """
        if (
            not callable(getattr(anchor, "read_checkpoint", None))
            or not callable(getattr(anchor, "compare_and_advance", None))
        ):
            raise TypeError("external_audit_anchor_required")
        try:
            anchor_sequence, anchor_digest = anchor.read_checkpoint()
        except Exception:
            raise RuntimeError("external_audit_anchor_unavailable") from None

        # Detect local rollback or same-sequence divergence before any advance.
        self.verify_against_anchor(anchor_sequence, anchor_digest)
        local_sequence, local_digest = self.checkpoint()
        if local_sequence == anchor_sequence:
            return local_sequence, local_digest

        try:
            advanced = anchor.compare_and_advance(
                anchor_sequence, anchor_digest, local_sequence, local_digest
            )
        except Exception:
            raise RuntimeError("external_audit_anchor_unavailable") from None
        if advanced is not True:
            # Another writer may have advanced the anchor concurrently.
            try:
                observed_sequence, observed_digest = anchor.read_checkpoint()
            except Exception:
                raise RuntimeError("external_audit_anchor_unavailable") from None
            if (observed_sequence, observed_digest) != (local_sequence, local_digest):
                self.verify_against_anchor(observed_sequence, observed_digest)
                raise RuntimeError("external_audit_anchor_advance_conflict")
        try:
            confirmed = anchor.read_checkpoint()
        except Exception:
            raise RuntimeError("external_audit_anchor_unavailable") from None
        if confirmed != (local_sequence, local_digest):
            self.verify_against_anchor(*confirmed)
            raise RuntimeError("external_audit_anchor_confirmation_mismatch")
        return local_sequence, local_digest

    def digest(self) -> str:
        """Return the current digest only after verifying the complete chain."""
        return self.checkpoint()[1]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
