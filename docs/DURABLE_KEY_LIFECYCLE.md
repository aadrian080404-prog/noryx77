# Durable Key Lifecycle Metadata

`core.DurableKeyLifecycle` persists key metadata transitions (register, rotate, retire, revoke) in an authenticated SQLite event chain. The journal records key IDs, versions and lifecycle states only; raw encryption/signing key material remains outside NORYX7 behind an external KMS/HSM boundary.

Every event is canonicalized and authenticated with HMAC-SHA256, chained to the preceding event, and validated during recovery. The lifecycle transition is persisted before the in-memory state changes. Invalid transitions are rejected before persistence.

## Limits

- This component stores lifecycle metadata, not key material and not KMS credentials.
- It is a single-host/single-process state machine, not distributed key-management consensus.
- Full SQLite snapshot rollback requires an external monotonic witness.
- KMS/HSM provider integration, key re-encryption migration, backup/recovery and multi-region revocation propagation are not included.
