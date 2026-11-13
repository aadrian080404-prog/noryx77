# NORYX7 Runtime Durable Journal

Status: implementation candidate in PR #14; not yet CI-verified or deployed.

## What is implemented

`noryx7_runtime.SQLiteStateJournal` is an optional persistent implementation of the runtime-level `StateJournal` contract. It subclasses the existing in-memory journal, so the runtime's signature verifier, trusted-identity checks, attestation validation, per-execution principal binding, action digest reservation and per-execution attestation chain remain in force.

It persists three append-only event types:

- `reserve`: pre-dispatch binding of execution, principal, step and action digest.
- `append`: a verified, signed runtime attestation.
- `rollback`: a compensating event that removes the most recent in-memory attestation and restores its reservation; the persisted event history is not destructively rewritten.

Each event is canonicalized and authenticated with HMAC-SHA256. The key is injected by the caller and must come from a secret manager outside the SQLite file. SQLite uses WAL, FULL synchronous commits, busy timeout, foreign keys, trusted-schema restrictions and restrictive file permissions on POSIX.

Startup replays the complete event chain, validates sequence continuity, payload digest, HMAC, event schema and key ID, then passes recovered attestations back through the original signature and identity verification logic. Unresolved reservations survive restart and remain visible as uncertain/incomplete work; they are not silently treated as completed.

A stale concurrent writer is rejected by comparing its remembered head with the actual SQLite head inside an IMMEDIATE transaction. A storage failure poisons the instance and subsequent operations fail closed.

## Explicit limitations

- HMAC and a hash chain detect modification/reordering but do not prevent rollback of the entire SQLite database to an older valid snapshot.
- There is no external monotonic anchor/witness transaction in this implementation.
- There is no KMS/HSM adapter, key rotation, key recovery, or multi-key historical verification yet.
- SQLite is a single-host persistence backend, not a distributed consensus or replicated journal.
- A reservation surviving a crash cannot prove whether an external side effect happened before the crash. Recovery must classify it as an uncertain outcome and reconcile through an idempotent external operation or operator review.
- The class is optional and must be explicitly injected into `RuntimeEngine`; the existing default `StateJournal` remains in-memory.
- The current PR adds focused tests but has not yet passed its CI workflows.

## Safe construction

The caller must provide an absolute database path, at least 32 bytes of externally held integrity key material, a stable key ID, the trusted attestation verifier, and (where required) the trusted identity registry and runtime ID. Never store the integrity key in the database, repository, event payload or logs.

This implementation is a durability improvement, not a production anti-rollback claim.
