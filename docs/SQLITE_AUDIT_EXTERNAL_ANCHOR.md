# SQLite audit external anti-rollback anchor

SQLiteAuditLog now exposes verify_and_advance_anchor(anchor), using the
MonotonicAnchor contract. It verifies the complete local hash chain and checks
that the external anchor's sequence and MAC match the corresponding local
prefix. If the database is shorter than the external sequence, it reports a
rollback. If the prefix digest differs, it reports a chain mismatch.

A valid local tail beyond the anchor can be advanced with compare-and-swap.
This is intentional crash recovery for the case where a process committed a
local audit event but stopped before updating the external witness. The method
never silently accepts a shorter or divergent database.

The anchor must live outside the audit database's rollback domain. An
InMemoryMonotonicAnchor is test-only. Production should supply an independently
operated RemoteMonotonicAnchor or QuorumMonotonicAnchor with separately
protected keys, hosts and storage. This method does not itself provision a
remote service or guarantee witness independence.


If a compare-and-swap call raises after a remote witness may have committed the
replacement, the client reads the witness back. An exact replacement confirms
the transition; an unavailable or divergent read-back returns
audit_anchor_outcome_uncertain and never assumes success. A rejected CAS whose
read-back is unavailable is also treated as uncertain. Callers must reconcile
that state before retrying a side effect.
