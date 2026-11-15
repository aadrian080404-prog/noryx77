import pytest
from .matrix_ledger import LedgerRequest, LocalDoubleEntryLedger


def req(**kw):
    values = dict(tenant_id="t1", idempotency_key="transfer-1", asset_id="EUR-cent",
                  debit_account="wallet-a", credit_account="wallet-b", amount_minor=1250)
    values.update(kw)
    return LedgerRequest(**values)


def allow(_request, proof):
    return proof == b"authorized"


def test_ledger_posts_balanced_integer_minor_units_and_reopens(tmp_path):
    path = tmp_path / "ledger.db"
    ledger = LocalDoubleEntryLedger(path)
    posted = ledger.post(req(), b"authorized", allow)
    assert not posted.replayed
    assert ledger.balance("t1", "EUR-cent", "wallet-a") == -1250
    assert ledger.balance("t1", "EUR-cent", "wallet-b") == 1250
    reopened = LocalDoubleEntryLedger(path)
    replay = reopened.post(req(), b"authorized", allow)
    assert replay.replayed and replay.journal_id == posted.journal_id
    assert reopened.balance("t1", "EUR-cent", "wallet-a") == -1250


def test_ledger_requires_external_authorization(tmp_path):
    ledger = LocalDoubleEntryLedger(tmp_path / "ledger.db")
    with pytest.raises(PermissionError, match="ledger_authorization_denied"):
        ledger.post(req(), b"no", allow)


def test_ledger_rejects_idempotency_conflict_and_float_amount(tmp_path):
    ledger = LocalDoubleEntryLedger(tmp_path / "ledger.db")
    ledger.post(req(), b"authorized", allow)
    with pytest.raises(PermissionError, match="ledger_idempotency_conflict"):
        ledger.post(req(amount_minor=1300), b"authorized", allow)
    with pytest.raises(ValueError, match="amount_must_be_positive_int64_minor_units"):
        ledger.post(req(idempotency_key="float", amount_minor=1.5), b"authorized", allow)


def test_ledger_rejects_same_account(tmp_path):
    ledger = LocalDoubleEntryLedger(tmp_path / "ledger.db")
    with pytest.raises(ValueError, match="debit_and_credit_accounts_must_differ"):
        ledger.post(req(credit_account="wallet-a"), b"authorized", allow)


def test_ledger_journal_rows_are_append_only(tmp_path):
    import sqlite3
    path = tmp_path / "ledger.db"
    ledger = LocalDoubleEntryLedger(path)
    posted = ledger.post(req(), b"authorized", allow)
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="journal_is_append_only"):
            db.execute("UPDATE matrix_journal SET amount_minor=1 WHERE journal_id=?", (posted.journal_id,))
        with pytest.raises(sqlite3.IntegrityError, match="postings_are_append_only"):
            db.execute("DELETE FROM matrix_postings WHERE journal_id=?", (posted.journal_id,))
