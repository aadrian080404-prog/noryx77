# Durable Agent Identity Registry v1

## Stored state

The SQLite registry persists only an agent identifier, its Ed25519 public key,
a monotonically increasing generation, an active/revoked state and an update
timestamp. Private key material is never stored in this database.

## Registration and rotation

A new identifier is registered at generation 1. Rotation requires both the
currently trusted key and the proposed replacement key to sign the same
domain-separated statement containing the agent identifier, expected
generation, old public key and new public key.

The registry serializes writers with SQLite `BEGIN IMMEDIATE`, checks the
expected generation and commits the new public key and next generation in one
transaction. Concurrent stale rotations are rejected.

## Revocation and recovery

Revocation is terminal for that identifier. It removes the active public key
but preserves a tombstone and generation. Re-registration of the same
identifier is rejected. After compromise, recovery must provision a new
identifier through an independently authorized process.

## Boundaries

- The database stores public trust metadata, not private keys.
- SQLite serializes processes sharing the same database file; it is not a
  distributed consensus service across hosts or independent databases.
- A privileged attacker able to roll back the database can roll back the
  generation. Production rollback resistance needs an external monotonic
  witness or hardware-backed counter.
- The registry implements the same trust interface as the in-memory registry,
  but production runtime wiring and principal-agent admission integration are
  separate follow-up work.
