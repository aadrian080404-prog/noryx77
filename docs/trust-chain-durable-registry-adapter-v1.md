# Trust Chain Durable Registry Adapter v1

The trust chain now accepts the structural `IdentityTrustRegistry` contract
instead of requiring the concrete in-memory `IdentityRegistry` class.

Both the in-memory registry and `SQLiteAgentIdentityRegistry` implement the
same trust checks: current public key must match the identity, and the
identity must remain active. Attestation verification uses that live check
before accepting trust evidence.

This change makes the durable registry usable by TrustChain without changing
the evidence format, channel binding, device checks or replay guard.

The adapter does not by itself persist replay-guard state, configure a KMS/HSM,
or connect principal-agent admission. Those remain independent integration
boundaries. The SQLite registry remains limited to a shared database file,
not multi-host consensus.
