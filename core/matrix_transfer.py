"""Crash-recoverable two-participant transfer coordinator contract.

This persists protocol intent and progress locally. It is not a payment rail:
participants must provide durable, idempotent prepare/commit/abort operations.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Iterator, Protocol


class TransferParticipant(Protocol):
    participant_id: str
    def prepare(self, transfer_id: str, asset_id: str, amount_minor: int,
                request_digest: str) -> None: ...
    def commit(self, transfer_id: str, request_digest: str) -> None: ...
    def abort(self, transfer_id: str, request_digest: str) -> None: ...


@dataclass(frozen=True)
class TransferRequest:
    transfer_id: str
    source_id: str
    destination_id: str
    asset_id: str
    amount_minor: int


@dataclass(frozen=True)
class TransferStatus:
    transfer_id: str
    state: str
    source_prepared: bool
    destination_prepared: bool
    source_committed: bool
    destination_committed: bool
    request_digest: str


class DurableTransferCoordinator:
    """Local write-ahead state machine for recoverable two-party transfers.

    The coordinator never declares COMMITTED until both participants confirm.
    Once COMMITTING begins it never attempts abort: recovery must finish commit
    or remain IN_DOUBT for operator intervention.
    """

    STATES = {"PREPARING", "PREPARED", "COMMITTING", "COMMITTED", "ABORTED", "IN_DOUBT"}
    MAX_MINOR = (1 << 63) - 1

    def __init__(self, database: str | Path, timeout: float = 5.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("positive_database_timeout_required")
        self.database = str(database)
        self.timeout = float(timeout)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_transfers (
                transfer_id TEXT PRIMARY KEY, request_digest TEXT NOT NULL,
                source_id TEXT NOT NULL, destination_id TEXT NOT NULL,
                asset_id TEXT NOT NULL, amount_minor INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN
                  ('PREPARING','PREPARED','COMMITTING','COMMITTED','ABORTED','IN_DOUBT')),
                source_prepared INTEGER NOT NULL DEFAULT 0,
                destination_prepared INTEGER NOT NULL DEFAULT 0,
                source_committed INTEGER NOT NULL DEFAULT 0,
                destination_committed INTEGER NOT NULL DEFAULT 0
            )""")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    @staticmethod
    def _digest(request: TransferRequest) -> str:
        payload = json.dumps({
            "transfer_id": request.transfer_id, "source_id": request.source_id,
            "destination_id": request.destination_id, "asset_id": request.asset_id,
            "amount_minor": request.amount_minor,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def _validate(cls, request: TransferRequest) -> None:
        if not isinstance(request, TransferRequest):
            raise TypeError("transfer_request_required")
        values = (request.transfer_id, request.source_id, request.destination_id, request.asset_id)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("transfer_identifiers_required")
        if request.source_id == request.destination_id:
            raise ValueError("transfer_participants_must_differ")
        amount = request.amount_minor
        if isinstance(amount, bool) or not isinstance(amount, int) or not 0 < amount <= cls.MAX_MINOR:
            raise ValueError("transfer_amount_must_be_positive_int64_minor_units")

    @staticmethod
    def _status(row) -> TransferStatus:
        return TransferStatus(row[0], row[1], bool(row[2]), bool(row[3]),
                              bool(row[4]), bool(row[5]), row[6])

    def status(self, transfer_id: str) -> TransferStatus | None:
        with self._connect() as db:
            row = db.execute("""SELECT transfer_id,state,source_prepared,destination_prepared,
                source_committed,destination_committed,request_digest
                FROM matrix_transfers WHERE transfer_id=?""", (transfer_id,)).fetchone()
        return self._status(row) if row else None

    def _ensure_intent(self, request: TransferRequest, digest: str) -> TransferStatus:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT transfer_id,state,source_prepared,destination_prepared,"
                "source_committed,destination_committed,request_digest FROM matrix_transfers "
                "WHERE transfer_id=?", (request.transfer_id,)).fetchone()
            if row:
                if row[6] != digest:
                    raise PermissionError("transfer_idempotency_conflict")
                db.commit()
                return self._status(row)
            db.execute("""INSERT INTO matrix_transfers
                (transfer_id,request_digest,source_id,destination_id,asset_id,amount_minor,state)
                VALUES (?,?,?,?,?,?,'PREPARING')""",
                (request.transfer_id,digest,request.source_id,request.destination_id,
                 request.asset_id,request.amount_minor))
            db.commit()
        return self.status(request.transfer_id)

    def _mark(self, transfer_id: str, column: str, value: int = 1,
              state: str | None = None) -> None:
        allowed = {"source_prepared", "destination_prepared", "source_committed",
                   "destination_committed"}
        if column not in allowed:
            raise ValueError("invalid_transfer_progress_field")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if state is None:
                db.execute(f"UPDATE matrix_transfers SET {column}=? WHERE transfer_id=?",
                           (value, transfer_id))
            else:
                db.execute(f"UPDATE matrix_transfers SET {column}=?,state=? WHERE transfer_id=?",
                           (value, state, transfer_id))
            db.commit()

    def _set_state(self, transfer_id: str, state: str) -> None:
        if state not in self.STATES:
            raise ValueError("invalid_transfer_state")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE matrix_transfers SET state=? WHERE transfer_id=?", (state, transfer_id))
            db.commit()

    def execute(self, request: TransferRequest, source: TransferParticipant,
                destination: TransferParticipant) -> TransferStatus:
        self._validate(request)
        if source.participant_id != request.source_id or destination.participant_id != request.destination_id:
            raise PermissionError("transfer_participant_binding_mismatch")
        digest = self._digest(request)
        self._ensure_intent(request, digest)
        return self._advance(request, digest, source, destination)

    def resume(self, transfer_id: str, source: TransferParticipant,
               destination: TransferParticipant) -> TransferStatus:
        status = self.status(transfer_id)
        if status is None:
            raise KeyError("unknown_transfer")
        if source.participant_id == destination.participant_id:
            raise ValueError("transfer_participants_must_differ")
        with self._connect() as db:
            row = db.execute("SELECT source_id,destination_id,asset_id,amount_minor FROM "
                             "matrix_transfers WHERE transfer_id=?", (transfer_id,)).fetchone()
        if row[0] != source.participant_id or row[1] != destination.participant_id:
            raise PermissionError("transfer_participant_binding_mismatch")
        request = TransferRequest(transfer_id, row[0], row[1], row[2], int(row[3]))
        return self._advance(request, status.request_digest, source, destination)

    def _advance(self, request: TransferRequest, digest: str,
                 source: TransferParticipant, destination: TransferParticipant) -> TransferStatus:
        current = self.status(request.transfer_id)
        if current.state in {"COMMITTED", "ABORTED"}:
            return current
        try:
            if current.state in {"PREPARING", "IN_DOUBT"} and not current.source_committed and not current.destination_committed:
                if not current.source_prepared:
                    source.prepare(request.transfer_id, request.asset_id, request.amount_minor, digest)
                    self._mark(request.transfer_id, "source_prepared")
                current = self.status(request.transfer_id)
                if not current.destination_prepared:
                    destination.prepare(request.transfer_id, request.asset_id, request.amount_minor, digest)
                    self._mark(request.transfer_id, "destination_prepared")
                self._set_state(request.transfer_id, "PREPARED")
            self._set_state(request.transfer_id, "COMMITTING")
            current = self.status(request.transfer_id)
            if not current.source_committed:
                source.commit(request.transfer_id, digest)
                self._mark(request.transfer_id, "source_committed")
            current = self.status(request.transfer_id)
            if not current.destination_committed:
                destination.commit(request.transfer_id, digest)
                self._mark(request.transfer_id, "destination_committed")
            self._set_state(request.transfer_id, "COMMITTED")
        except Exception:
            self._set_state(request.transfer_id, "IN_DOUBT")
            raise
        return self.status(request.transfer_id)
