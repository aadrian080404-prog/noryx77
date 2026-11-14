# HTTPS/mTLS transport for distributed memory

This transport carries the signed event batches from PR #52 over HTTPS. Both
directions require TLS 1.2 or newer; the client validates the server
certificate and hostname, while the server requires a client certificate from
a configured CA. The payload is independently authenticated by the sender's
Ed25519 identity and checked against the receiving identity registry.

The endpoint accepts only bounded canonical event batches, rejects unexpected
fields and transfer-encoding ambiguity, and returns a minimal inserted-event
count. Duplicate delivery is idempotent at the event-store layer. Bodies and
credentials are not logged.

This is a point-to-point transport, not a quorum protocol. Production still
needs peer authorization tied to certificate identity, certificate revocation
and rotation, rate limiting, replay/abuse monitoring, peer discovery,
authenticated vector-clock exchange, and a recovery/anti-rollback strategy.
