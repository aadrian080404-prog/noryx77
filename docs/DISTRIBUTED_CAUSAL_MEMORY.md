# Distributed causal memory

This component is an offline-first, transport-neutral replication layer.

- SQLite WAL/FULL event persistence.
- Stable per-database actor identity.
- Immutable events with canonical SHA-256 identifiers.
- Vector clocks for causal ordering.
- Idempotent batch exchange through `export_since` and `merge`.
- Concurrent writes are retained and exposed through `conflicts`; the visible
  winner is selected deterministically, never by arrival order.
- Deletes are tombstones and replicate like other events.
- Actor/counter equivocation is rejected.

## Explicit boundary

This is not a network transport, distributed consensus protocol, global
identity service, or anti-rollback authority. A production adapter must
authenticate peers, bind actor IDs to durable identities, enforce authorization,
rate/size limits and replay policy, and use an independent monotonic witness
or quorum to detect restoration of old node snapshots. The local SQLite
database is not protected against a privileged host administrator.
