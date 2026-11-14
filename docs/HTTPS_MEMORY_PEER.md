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


## TLS certificate to agent identity binding

The server now requires an explicit `peer_certificate_agents` mapping from the
lowercase SHA-256 fingerprint of each CA-validated client certificate to one
AgentIdentity `agent_id`. The authenticated certificate fingerprint is checked
against this mapping before a batch is accepted, and the signed batch identity
must name the same agent. The normal AgentIdentity signature and trust-registry
checks still run; mTLS does not replace them.

The listener also applies a bounded socket read timeout and a configurable
maximum number of concurrent request threads. These limits reduce slow-client
and thread-exhaustion exposure; they are not a substitute for network-level
rate limiting or a reverse proxy.

Example mapping (fingerprints are provisioned out of band):

```python
make_memory_peer_server(
    store, registry, host="127.0.0.1", port=9443,
    cert_file="server.pem", key_file="server.key",
    client_ca_file="peer-ca.pem",
    peer_certificate_agents={"<64-char-sha256-fingerprint>": "agent-17"},
)
```
