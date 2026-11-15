"""Minimal local double-entry journal reference; not a payment or custody system."""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class LedgerRequest:
    tenant_id: str
    idempotency_key: str
    asset_id: str
    debit_account: str
    credit_account: str
    amount_minor: int


@dataclass(frozen=True)
class LedgerPosting:
    request: LedgerRequest
    journal_id: int
    replayed: bool


class LocalDoubleEntryLedger:
    """Append-only balanced postings with external authorization verification.

    Amounts are integer minor units. The injected verifier must independently
    authorize the exact immutable request; this local journal does not settle money.
    """
    MAX_MINOR = (1 << 63) - 1

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_journal (
                journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                asset_id TEXT NOT NULL, debit_account TEXT NOT NULL,
                credit_account TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
                UNIQUE(tenant_id, idempotency_key))""")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_postings (
                journal_id INTEGER NOT NULL, asset_id TEXT NOT NULL,
                account_id TEXT NOT NULL, amount_minor INTEGER NOT NULL,
                FOREIGN KEY(journal_id) REFERENCES matrix_journal(journal_id))""")

    def post(self, request: LedgerRequest, authorization_proof: bytes,
             authorize: Callable[[LedgerRequest, bytes], bool]) -> LedgerPosting:
        fields = (request.tenant_id, request.idempotency_key, request.asset_id,
                  request.debit_account, request.credit_account)
        if any(not isinstance(v, str) or not v.strip() for v in fields):
            raise ValueError("ledger_identifiers_required")
        amount = request.amount_minor
        if isinstance(amount, bool) or not isinstance(amount, int) or not 0 < amount <= self.MAX_MINOR:
            raise ValueError("amount_must_be_positive_int64_minor_units")
        if request.debit_account == request.credit_account:
            raise ValueError("debit_and_credit_accounts_must_differ")
        if not isinstance(authorization_proof, bytes) or not callable(authorize):
            raise ValueError("authorization_proof_and_verifier_required")
        if authorize(request, authorization_proof) is not True:
            raise PermissionError("ledger_authorization_denied")

        with sqlite3.connect(self.database, timeout=5, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                """SELECT journal_id, asset_id, debit_account, credit_account, amount_minor
                   FROM matrix_journal WHERE tenant_id=? AND idempotency_key=?""",
                (request.tenant_id, request.idempotency_key)).fetchone()
            if previous:
                expected = (request.asset_id, request.debit_account, request.credit_account, amount)
                if tuple(previous[1:]) != expected:
                    raise PermissionError("ledger_idempotency_conflict")
                db.commit()
                return LedgerPosting(request, int(previous[0]), True)
            cursor = db.execute(
                """INSERT INTO matrix_journal
                   (tenant_id,idempotency_key,asset_id,debit_account,credit_account,amount_minor)
                   VALUES (?,?,?,?,?,?)""",
                (request.tenant_id, request.idempotency_key, request.asset_id,
                 request.debit_account, request.credit_account, amount))
            journal_id = int(cursor.lastrowid)
            db.executemany(
                "INSERT INTO matrix_postings(journal_id,asset_id,account_id,amount_minor) VALUES (?,?,?,?)",
                ((journal_id, request.asset_id, request.debit_account, -amount),
                 (journal_id, request.asset_id, request.credit_account, amount)))
            db.commit()
        return LedgerPosting(request, journal_id, False)

    def balance(self, tenant_id: str, asset_id: str, account_id: str) -> int:
        with sqlite3.connect(self.database) as db:
            row = db.execute(
                """SELECT COALESCE(SUM(p.amount_minor),0)
                   FROM matrix_postings p JOIN matrix_journal j USING(journal_id)
                   WHERE j.tenant_id=? AND p.asset_id=? AND p.account_id=?""",
                (tenant_id, asset_id, account_id)).fetchone()
        return int(row[0])
