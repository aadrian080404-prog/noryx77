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


## Certificate-to-agent binding and resource limits

The server requires an explicit mapping from SHA-256 fingerprints of the
client leaf certificates (DER encoding, lowercase hexadecimal) to NORYX7
agent IDs. A CA-valid certificate is not sufficient: the presented signed
memory batch must name the exact agent pinned to that certificate. Certificate
rotation therefore requires an intentional pin update and overlapping
deployment procedure; do not use a broad CA trust list as an identity map.

The HTTP listener caps concurrent worker threads and applies a per-accepted
socket timeout to constrain slow or stalled clients. Configure a worker cap
appropriate to available memory and CPU. These controls complement, but do
not replace, an upstream connection-rate limit, network firewall, certificate
revocation process, and operational monitoring.
