# Durable Agent Identity Registry

`core.DurableIdentityRegistry` persists agent trust-anchor registration and revocation events in SQLite. Each canonical event is chained with HMAC-SHA256 and includes a sequence number, previous MAC, schema version and key ID. Recovery replays only after verifying the entire chain.

The integrity key is supplied by the caller and must be provisioned outside the database. The registry rejects malformed records, chain gaps, wrong key IDs and altered events. Registration and revocation are serialized with the registry lock and persisted before changing the in-memory trust map.

## Limits

- This is a single-host, single-process registry, not a distributed consensus service.
- Full database snapshot rollback is not detected without an external monotonic witness.
- KMS/HSM provisioning, key rotation, trust-root bootstrap and signed administrative audit are not included.
- Revocation becomes effective in this registry after its durable event commits; remote replicas are not synchronized by this class.
