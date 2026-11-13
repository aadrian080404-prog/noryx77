# Durable Security Event Stream

`core.DurableSecurityEventBus` persists structured security events in SQLite and authenticates each canonical event with an HMAC-SHA256 chain. Startup verifies sequence continuity, schema/key identity and every record MAC before exposing recovered events. POSIX permissions are restricted for the database and existing WAL/SHM sidecars.

Only structured metadata and an evidence digest are stored; raw sensitive evidence is not captured by this bus. The integrity key must be supplied from an external secret boundary.

## Limits

- Single-process local event persistence; no remote collector, distributed ordering or cross-host consensus.
- Full database rollback and deletion of an entire valid suffix require an external monotonic witness to detect.
- No alert delivery, automated containment, incident case management or retention/compaction policy is implemented.
- Evidence digests do not prove that the underlying evidence was authentic; source verification remains the responsibility of the evidence pipeline.
