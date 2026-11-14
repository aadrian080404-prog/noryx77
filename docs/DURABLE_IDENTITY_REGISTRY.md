# Durable agent identity trust registry

`SQLiteIdentityRegistry` persists public-key trust anchors and revocation
state across process restarts. It stores public keys only; private signing
material remains outside this registry.

## Guarantees in this component

- SQLite WAL and FULL synchronous commits for durable metadata.
- Unique agent identity registration.
- Fail-closed validation of persisted identity rows.
- Revocation is retained as a tombstone and survives restart.
- `with_trusted_identity` serializes a bounded verification/commit callback
  against revocation across connections sharing the database.

## Explicit limits

This is a local durable registry, not a distributed consensus service. It does
not replicate trust state across hosts, provide quorum revocation, protect
against restoration of an old database snapshot, or replace an HSM/KMS. The
critical-section callback must not perform network I/O or invoke agent code.
Remote nodes need an authenticated replication protocol and independent
anti-rollback authority before this registry can be treated as global trust.
