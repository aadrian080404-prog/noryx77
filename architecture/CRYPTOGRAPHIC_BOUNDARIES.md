# Cryptographic boundaries

NORYX7 uses cryptography to bind data to the correct security context; cryptography does not replace authorization.

## Primitives

- **Ed25519**: agent identity and result attestation signatures.
- **AES-256-GCM**: authenticated encryption for bounded payloads.
- **HKDF-SHA256**: domain-separated subkey derivation.
- **HMAC-SHA256**: provenance/evidence seals where symmetric authenticity is appropriate.
- **SHA-256**: canonical content and chain digests.

## Binding requirements

Every security-sensitive digest/signature domain includes the identifiers that determine authority: execution, principal, agent/runtime identity, action/result content and chain predecessor where applicable.

Cross-runtime, cross-principal, cross-agent-key, reordered-chain, replayed and retargeted artifacts must be rejected.

## Key boundary

Production private keys must remain behind a platform/KMS/secure-keystore boundary. `InMemoryKeyProvider` is test-only and must never be treated as production key storage.

## Fail-closed rule

Malformed envelopes, invalid signatures, invalid digests, missing provenance pairs, unknown key IDs and verification exceptions are errors—not partially trusted input.
