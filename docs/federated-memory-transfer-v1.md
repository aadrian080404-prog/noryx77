# NORYX7 Federated Memory Transfer v1

## Purpose and trust boundaries

This protocol transfers an opaque memory payload between runtimes without treating transport success as execution authority. The source and destination runtimes retain their own identity, key, audit, policy, and ActionGate boundaries.

The envelope is not a capability grant. The receiving runtime must independently authenticate its local PrincipalIdentity and AgentIdentity, enforce memory namespace policy, record the transfer in its audit stream, and pass any later action through its local ActionGate.

## Cryptographic construction

1. The sender creates a fresh ephemeral X25519 key pair.
2. It derives a shared secret with the recipient's authenticated X25519 public key.
3. HKDF-SHA256 derives a 32-byte key using the canonical transfer metadata hash as salt and the protocol-specific info string.
4. ChaCha20-Poly1305 encrypts the memory payload. The authenticated associated data binds schema version, transfer ID, source and recipient principals, source and recipient agents, execution ID, recipient key ID, issuer key ID, issue/expiry times, replay nonce, ephemeral public key, and AEAD nonce.
5. The sender computes the ciphertext SHA-256 digest and signs the canonical JSON envelope (all fields except the signature) with its Ed25519 issuer key.
6. The receiver resolves the issuer key ID from its trusted local federation trust store and independently verifies that this issuer key is bound to the claimed source principal. A key supplied by the envelope is never trusted.
7. For agent-scoped transfers, the receiver independently verifies both the source principal/agent pair against federation identity trust and the recipient principal/agent pair against its local AgentIdentity registry. Both callbacks are mandatory; otherwise the transfer is rejected.

The payload is encrypted to the recipient's key. The receiver decrypts only after schema, destination identity, time window, ciphertext digest, and issuer signature have been validated and the replay nonce has been atomically reserved.

## Envelope fields

- `schema_version`: fixed protocol version.
- `transfer_id`: unique transfer identifier.
- `source_principal_id`, `recipient_principal_id`: authenticated principal binding.
- `source_agent_id`, `recipient_agent_id`: either both empty for principal-shared scope or both populated for an explicitly mapped agent transfer.
- `execution_id`: source execution ownership context.
- `recipient_key_id`: key identifier expected by the recipient runtime.
- `ephemeral_public_key_b64`, `aead_nonce_b64`: ephemeral X25519 public key and 96-bit AEAD nonce.
- `ciphertext_b64`, `ciphertext_sha256`: encrypted payload and integrity digest.
- `issued_at`, `expires_at`, `nonce`: bounded lifetime and one-shot replay identifier.
- `issuer_key_id`, `signature`: trusted issuer key reference and Ed25519 signature.

Unknown and missing fields are rejected. Plaintext is never an accepted envelope field.

## Replay and persistence

`SQLiteNonceRegistry` uses a unique key on issuer key ID plus nonce and an immediate SQLite transaction. The reservation survives process restart when the same database is reused. It is a single-database primitive, not distributed consensus: multiple hosts must share one strongly consistent database or use a dedicated atomic nonce service. Separate host-local SQLite files are not sufficient for cluster-wide replay protection.

Expired nonce records may be pruned only after their expiry. A nonce is reserved before decryption, so an authenticated but undecryptable envelope cannot be retried with the same nonce.

## Fail-closed receiver sequence

1. Validate the exact envelope schema and field bounds.
2. Verify recipient principal and recipient key ID against local trusted context.
3. Enforce timestamp and maximum TTL constraints.
4. Validate base64, ciphertext size, encryption metadata, and ciphertext digest.
5. Verify Ed25519 signature using a locally resolved issuer key.
6. Verify issuer-key-to-source-principal binding. For agent scope, verify both source and recipient principal/agent bindings.
7. Atomically reserve the nonce in durable storage.
8. Decrypt with the local recipient private key and verify the AEAD tag.
9. Apply local agent-memory scope policy and append a redacted audit event.
10. Keep all subsequent operations subject to local authorization and ActionGate checks.

Any failed step rejects the transfer. Transport acceptance never bypasses policy or authorizes an action.

## Current implementation boundary

The primary runtime provides the v1 envelope, Ed25519 verifier adapter, X25519/ChaCha20-Poly1305 sealing and opening helpers, issuer/principal and agent-binding callback gates, and SQLite nonce registry. The secondary runtime has begun adding authenticated agent-scoped persistence. Production federation still requires wiring these helpers to the real identity/trust stores, durable audit sink, recipient key lifecycle, and a shared cluster-grade nonce service where more than one host participates.
