# Signed peer replication

The signed replication adapter binds each immutable memory event batch to an
Ed25519 agent identity. The receiver checks the exact canonical statement,
validates sender-to-event actor binding, verifies the signature, and requires
the identity registry to trust the sender before applying the batch.

Verification and the bounded local SQLite merge execute inside
`with_trusted_identity`, so local revocation cannot interleave with acceptance.
Duplicate event replay is idempotent through the underlying event log; actor
counter equivocation is rejected.

The adapter does not provide a network transport, peer discovery, key
distribution, quorum consensus, rate limiting across a network, or protection
against restoring old database snapshots. The registry must be durable and
replicated under an independently authenticated policy before multi-host use.
