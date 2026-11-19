# Federated memory transfer trust-store wiring v1

This adapter wires the v1 memory-transfer callbacks to the primary runtime's
durable principal and agent identity registries.

## Trust mapping

- The v1 profile requires `issuer_key_id == source_principal_id`. The
  Ed25519 verifier resolves the public key from the live
  `SQLitePrincipalIdentityRegistry`; no envelope-supplied key is accepted.
- Source principal binding is re-read from the same registry on every check.
  Missing, revoked, malformed, or unavailable identities deny the transfer.
- Agent identity is checked against `SQLiteIdentityRegistry` on every check.
  Revocation is therefore observed without a process-local key cache.
- Agent ownership is deliberately a distinct relationship. The adapter
  requires an explicit `is_agent_owned_by_principal(principal_id, agent_id)`
  callback backed by an authoritative binding store. A valid AgentIdentity
  does not by itself establish which principal owns it.

## Runtime integration

Construct the adapter from the runtime's durable principal registry, durable
agent registry, and authenticated principal-agent binding verifier. Pass its
four callbacks to `open_memory_transfer` or to the receiver's atomic import
method. The destination principal/agent identity must still come from the
authenticated local session, not request fields.

## Limits

- This is a local trust-store adapter, not an identity provider or provisioning
  workflow.
- The principal-to-agent relationship store remains an injected dependency
  because the current identity registries store identities separately.
- SQLite durability applies to one shared database file/store. It does not
  establish multi-host consensus or cluster-wide revocation propagation.
- Imported memory remains passive data. The receiving runtime must use its
  own ActionGate and audit policy before any action based on that memory.
