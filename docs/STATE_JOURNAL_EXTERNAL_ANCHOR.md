# State Journal External Monotonic Anchor

Status: implementation candidate in PR #19; CI not yet verified.

## Implemented

`StateJournal` can now be configured with a `MonotonicAnchor` implementation from `core.journal_integrity`.

- `require_external_anchor=True` rejects a missing anchor at construction.
- Every recovery validates the complete HMAC record chain, then compares the journal head with the external anchor.
- Exact head equality is accepted.
- A single-record gap is repairable only when the database head is exactly one sequence ahead and that final record's authenticated `previous_mac` equals the external anchor MAC. The journal attempts one compare-and-swap to advance the anchor.
- Any other mismatch fails closed. A database shorter than the external anchor is treated as rollback.
- After an append commits to SQLite, the journal advances the external anchor. If the process dies between the DB commit and anchor CAS, the next recovery can repair the single-step gap.

## Crash semantics

SQLite commit and an external monotonic service cannot be made one atomic transaction without a shared transaction protocol. This implementation uses a recoverable two-step protocol:

1. Authenticate and append the record in SQLite with WAL + FULL synchronous mode.
2. Advance the external anchor with compare-and-swap.
3. If step 2 fails, report an uncertain append outcome. The durable DB record is not silently deleted or rolled back. Recovery verifies it and retries only the one-step anchor transition.

Callers must treat an anchor-update error as an uncertain commit, then reopen/recover before retrying the business operation. They must not assume the record was absent just because the append raised after the SQLite commit.

## Deployment boundary

The in-memory anchor is test-only and is not rollback-resistant across process or host compromise. Production requires a real monotonic anchor outside the SQLite backup/restore/rollback domain, with authenticated transport, durable compare-and-swap semantics, access control, high availability and audited recovery.

The optional anchor preserves compatibility for existing callers. A deployment that requires rollback protection must explicitly pass a production anchor and set `require_external_anchor=True`.

This does not implement KMS/HSM key lifecycle, anchor quorum, distributed failover or a production anti-rollback service.
