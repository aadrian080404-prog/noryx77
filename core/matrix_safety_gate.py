"""Fail-closed two-person command permit gate for critical-system adapters.

The gate issues/consumes one-time permits only. It never executes commands or
replaces a certified local safety controller or actuator interlock.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
import secrets
import sqlite3
from typing import Callable, Iterator


@dataclass(frozen=True)
class CommandPermit:
    proposal_id: str
    resource_id: str
    command_digest: str
    expires_at: int
    token: str


class DurableSafetyGate:
    def __init__(self, database: str, *,
                 authorize_operator: Callable[[str, str, str], bool],
                 interlock_check: Callable[[str, str], bool],
                 timeout: float = 5.0) -> None:
        if not isinstance(database, str) or not database:
            raise ValueError("database_path_required")
        if not callable(authorize_operator) or not callable(interlock_check):
            raise ValueError("operator_authorizer_and_interlock_required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout_must_be_finite_and_positive")
        self.database = database
        self.authorize_operator = authorize_operator
        self.interlock_check = interlock_check
        self.timeout = float(timeout)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS safety_proposals (
                proposal_id TEXT PRIMARY KEY,
                proposer_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                command_digest TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','ISSUED','EXPIRED','CONSUMED'))
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS safety_approvals (
                proposal_id TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                approved_at INTEGER NOT NULL,
                PRIMARY KEY(proposal_id,operator_id),
                FOREIGN KEY(proposal_id) REFERENCES safety_proposals(proposal_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS safety_permits (
                proposal_id TEXT PRIMARY KEY,
                token_digest TEXT NOT NULL UNIQUE,
                consumed INTEGER NOT NULL DEFAULT 0 CHECK(consumed IN (0,1)),
                FOREIGN KEY(proposal_id) REFERENCES safety_proposals(proposal_id)
            )""")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    @staticmethod
    def _required(value: str, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(field + "_required")

    @staticmethod
    def _now(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("now_must_be_nonnegative_integer")

    def propose(self, proposal_id: str, proposer_id: str, resource_id: str,
                command: bytes, expires_at: int, *, now: int) -> str:
        for value, field in ((proposal_id, "proposal_id"), (proposer_id, "proposer_id"),
                             (resource_id, "resource_id")):
            self._required(value, field)
        self._now(now)
        if not isinstance(command, bytes) or not command:
            raise ValueError("nonempty_command_bytes_required")
        if isinstance(expires_at, bool) or not isinstance(expires_at, int) or expires_at <= now:
            raise ValueError("proposal_expiry_must_be_in_future")
        digest = hashlib.sha256(command).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT proposer_id,resource_id,command_digest,expires_at FROM safety_proposals WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()
            expected = (proposer_id, resource_id, digest, expires_at)
            if previous is not None:
                if previous != expected:
                    db.rollback()
                    raise PermissionError("proposal_id_conflict")
                db.commit()
                return digest
            db.execute(
                "INSERT INTO safety_proposals VALUES(?,?,?,?,?,'PENDING')",
                (proposal_id, proposer_id, resource_id, digest, expires_at),
            )
            db.commit()
        return digest

    def approve(self, proposal_id: str, operator_id: str, *, now: int) -> int:
        self._required(proposal_id, "proposal_id")
        self._required(operator_id, "operator_id")
        self._now(now)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT proposer_id,resource_id,command_digest,expires_at,state FROM safety_proposals WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                db.rollback()
                raise KeyError("proposal_not_found")
            if row[4] != "PENDING":
                db.rollback()
                raise PermissionError("proposal_not_pending")
            if row[3] <= now:
                db.execute("UPDATE safety_proposals SET state='EXPIRED' WHERE proposal_id=?", (proposal_id,))
                db.commit()
                raise PermissionError("proposal_expired")
            if operator_id == row[0]:
                db.rollback()
                raise PermissionError("proposer_cannot_approve")
            if not self.authorize_operator(operator_id, row[1], row[2]):
                db.rollback()
                raise PermissionError("operator_not_authorized")
            db.execute(
                "INSERT OR IGNORE INTO safety_approvals VALUES(?,?,?)",
                (proposal_id, operator_id, now),
            )
            count = db.execute(
                "SELECT COUNT(*) FROM safety_approvals WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()[0]
            db.commit()
        return count

    def issue(self, proposal_id: str, *, now: int) -> CommandPermit:
        self._required(proposal_id, "proposal_id")
        self._now(now)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT resource_id,command_digest,expires_at,state FROM safety_proposals WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                db.rollback()
                raise KeyError("proposal_not_found")
            if row[3] != "PENDING":
                db.rollback()
                raise PermissionError("proposal_not_pending")
            if row[2] <= now:
                db.execute("UPDATE safety_proposals SET state='EXPIRED' WHERE proposal_id=?", (proposal_id,))
                db.commit()
                raise PermissionError("proposal_expired")
            approvals = db.execute(
                "SELECT COUNT(DISTINCT operator_id) FROM safety_approvals WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()[0]
            if approvals < 2:
                db.rollback()
                raise PermissionError("two_distinct_approvals_required")
            if not self.interlock_check(row[0], row[1]):
                db.rollback()
                raise PermissionError("local_safety_interlock_blocked")
            token = secrets.token_urlsafe(32)
            token_digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            db.execute("INSERT INTO safety_permits(proposal_id,token_digest) VALUES(?,?)",
                       (proposal_id, token_digest))
            db.execute("UPDATE safety_proposals SET state='ISSUED' WHERE proposal_id=?", (proposal_id,))
            db.commit()
        return CommandPermit(proposal_id, row[0], row[1], row[2], token)

    def consume(self, permit: CommandPermit, command: bytes, *, now: int) -> bool:
        if not isinstance(permit, CommandPermit) or not isinstance(command, bytes):
            raise TypeError("permit_and_command_required")
        self._now(now)
        digest = hashlib.sha256(command).hexdigest()
        token_digest = hashlib.sha256(permit.token.encode("ascii")).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT p.resource_id,p.command_digest,p.expires_at,p.state,t.token_digest,t.consumed
                   FROM safety_proposals p JOIN safety_permits t ON t.proposal_id=p.proposal_id
                   WHERE p.proposal_id=?""",
                (permit.proposal_id,),
            ).fetchone()
            if row is None or row[4] != token_digest or row[5] != 0:
                db.rollback()
                raise PermissionError("permit_invalid_or_already_consumed")
            if row[3] != "ISSUED" or row[2] <= now or permit.expires_at != row[2]:
                db.rollback()
                raise PermissionError("permit_expired_or_inactive")
            if digest != row[1] or permit.command_digest != row[1] or permit.resource_id != row[0]:
                db.rollback()
                raise PermissionError("permit_command_or_resource_mismatch")
            if not self.interlock_check(row[0], row[1]):
                db.rollback()
                raise PermissionError("local_safety_interlock_blocked")
            db.execute("UPDATE safety_permits SET consumed=1 WHERE proposal_id=?", (permit.proposal_id,))
            db.execute("UPDATE safety_proposals SET state='CONSUMED' WHERE proposal_id=?", (permit.proposal_id,))
            db.commit()
        return True
