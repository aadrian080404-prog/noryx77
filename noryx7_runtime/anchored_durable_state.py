"""Runtime execution journal protected by an external monotonic anchor.

The anchor must live outside the SQLite database rollback domain. A test-only
in-memory anchor is not suitable for production deployment.
"""
from __future__ import annotations

from core.journal_integrity import AnchorSnapshot, MonotonicAnchor, ZERO_MAC

from .durable_state import DurableStateJournal


class AnchoredDurableStateJournal(DurableStateJournal):
    """Adds external anti-rollback protection to durable runtime reservations and attestations.

    A single committed local event ahead of the witness is treated as the known
    SQLite-commit-before-anchor-CAS crash window. Larger or inconsistent
    divergence fails closed.
    """

    def __init__(self, path: str, *, anchor: MonotonicAnchor, **kwargs) -> None:
        if not callable(getattr(anchor, "read", None)) or not callable(
            getattr(anchor, "compare_and_swap", None)
        ):
            raise TypeError("monotonic_anchor_contract_required")
        self._anchor = anchor
        super().__init__(path, **kwargs)
        try:
            with self._lock:
                self._reconcile_anchor_locked()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _local_head_locked(self) -> AnchorSnapshot:
        rows = self._db.execute(
            "SELECT sequence,event_json,previous_mac,record_mac,key_id,schema_version "
            "FROM runtime_events ORDER BY sequence"
        ).fetchall()
        expected_sequence = 1
        previous_mac = ZERO_MAC
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
            previous_mac = stored_mac
            expected_sequence += 1
        return AnchorSnapshot(expected_sequence - 1, previous_mac)

    def _validate_anchor_snapshot(self, snapshot: AnchorSnapshot) -> None:
        if (
            not isinstance(snapshot, AnchorSnapshot)
            or isinstance(snapshot.sequence, bool)
            or not isinstance(snapshot.sequence, int)
            or snapshot.sequence < 0
            or not isinstance(snapshot.mac, str)
            or len(snapshot.mac) != 64
        ):
            raise RuntimeError("runtime_journal_anchor_snapshot_invalid")
        try:
            bytes.fromhex(snapshot.mac)
        except ValueError as exc:
            raise RuntimeError("runtime_journal_anchor_snapshot_invalid") from exc

    def _reconcile_anchor_locked(self) -> AnchorSnapshot:
        local = self._local_head_locked()
        remote = self._anchor.read()
        self._validate_anchor_snapshot(remote)
        if remote == local:
            return local
        if local.sequence == remote.sequence + 1:
            row = self._db.execute(
                "SELECT previous_mac FROM runtime_events WHERE sequence=?",
                (local.sequence,),
            ).fetchone()
            if row is not None and row[0] == remote.mac:
                if self._anchor.compare_and_swap(remote, local):
                    return local
                if self._anchor.read() == local:
                    return local
        raise RuntimeError("runtime_journal_anchor_mismatch")

    def _persist(self, event: dict) -> None:
        with self._lock:
            previous = self._reconcile_anchor_locked()
            super()._persist(event)
            current = self._local_head_locked()
            if current.sequence != previous.sequence + 1:
                raise RuntimeError("runtime_journal_anchor_sequence_invalid")
            if not self._anchor.compare_and_swap(previous, current):
                if self._anchor.read() != current:
                    raise RuntimeError("runtime_journal_anchor_update_failed")

    def snapshot_anchor(self) -> AnchorSnapshot:
        with self._lock:
            return self._reconcile_anchor_locked()
