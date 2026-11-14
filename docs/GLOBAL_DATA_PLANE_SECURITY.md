# NORYX7 Global Data-Plane Security Architecture

Status: architecture baseline and implementation requirements. This document is not a production-readiness claim.

## 1. Security objective

NORYX7 is intended to move and protect data across devices, edge nodes, regional infrastructure and global services. It must handle personal, commercial, industrial, scientific, governmental and financial data without creating one central plaintext repository or one universal key.

The target security invariant is:

> A compromise of one account, process, device, region, service or operator must not grant access to unrelated tenants, data classes, keys, transaction domains or execution authorities.

"Nothing to take" is approached through data minimization, encryption, compartmentalization and short-lived access. It cannot mean that plaintext never exists: data must be available briefly to an authorised endpoint or computation boundary. That boundary must be isolated, measured, limited and auditable.

## 2. Four independent planes

### Data plane
- Carries payloads as authenticated ciphertext wherever possible.
- Uses tenant-, object-, purpose- and classification-bound associated data.
- Avoids plaintext payloads in routing metadata, telemetry, traces and error messages.
- Supports bounded streaming, backpressure, quotas and regional routing.
- Does not expose a global browseable index of raw customer content.

### Identity and policy plane
- Uses cryptographic identities, device posture, workload identity and short-lived capability grants.
- Evaluates every request against tenant, principal, purpose, data classification, destination, operation, risk and expiry.
- Revocation must propagate across regions with a defined maximum delay.
- A model-generated plan is never an authority. It is an untrusted proposal until policy and authorization approve it.

### Key plane
- Root keys remain in external HSM/KMS boundaries, not source code, application databases or model context.
- Uses envelope encryption: per-object data keys are wrapped by tenant- and purpose-scoped key-encryption keys.
- Supports key versioning, rotation, revocation, recovery and auditable break-glass procedures.
- No global master key should decrypt every tenant or every region.
- A key provider outage fails closed for protected writes and reads; there is no plaintext fallback.

### Transaction and execution plane
- Separates proposal, authorization, reservation, execution, verification, commit and reconciliation.
- High-impact operations require independent threshold approval bound to the exact canonical transaction statement and expiry.
- Every transaction needs an idempotency identity, immutable audit evidence and a defined outcome for uncertain external execution.
- Financial adapters must implement domain-specific rules; a generic tool call is not a bank or exchange integration.

## 3. Data lifecycle

1. Classify the data and determine the lawful purpose, tenant, retention and destination.
2. Generate a fresh per-object data key through the external KMS/HSM provider.
3. Encrypt at the earliest trusted boundary; bind tenant, record ID, purpose, classification, key version and schema into authenticated metadata.
4. Send only authenticated ciphertext over the transport.
5. Route by opaque identifiers and minimum required metadata.
6. Decrypt only inside an authorised execution boundary, with the shortest feasible key lifetime.
7. Return only the minimum required result; do not copy raw payloads into logs or audit events.
8. Expire caches, revoke capabilities and rotate keys according to policy.
9. Verify deletion and backup-retention behaviour; cryptographic erasure requires destruction of every usable wrapped-key path and its recoverable backups.

Large objects must use an authenticated chunked format with unique per-chunk nonces, authenticated chunk indexes, object-level manifests and truncation/reordering detection. The current per-record AES-GCM primitive is not yet a streaming storage implementation.

## 4. Network and system protection

- Mutual workload authentication; endpoint and workload identity bound to the session.
- AEAD transport encryption and integrity, not MAC-only plaintext framing.
- Fresh session IDs and key epochs; never reuse an AEAD nonce under the same key.
- Replay protection that survives process restart or requires a new session epoch after restart.
- Network segmentation by tenant, region, service and trust level.
- Deny-by-default service-to-service policy, egress allowlists and short-lived credentials.
- Signed build provenance, dependency/SBOM verification, reproducible builds where feasible, artifact signing and staged rollout.
- Runtime isolation, least-privilege OS identities, secret isolation, patching, intrusion detection, rate limits and DDoS protection.
- Recovery must assume a region or operator account can be compromised; restore from independently protected checkpoints.

## 5. High-impact transaction protocol

A transaction authorization statement must canonically bind at least:
- tenant and initiating principal;
- source and destination account or custody identity;
- asset/instrument, quantity, currency and price/limit;
- venue, market, order type and settlement conditions;
- fees, expiry, risk policy version and idempotency key;
- execution ID and the exact operation being approved.

The sequence is:

1. Validate identity, permissions, limits, account state and destination.
2. Simulate and independently verify the proposed transaction.
3. Obtain required independent signatures and check revocation/expiry.
4. Atomically reserve the idempotency key and relevant balance/position.
5. Submit through a domain-specific adapter using the same idempotency identity.
6. Verify the external receipt and settlement state.
7. Commit the local ledger and reconcile against the external system.
8. If the external outcome is unknown, quarantine the operation and reconcile; never blindly retry a non-idempotent side effect.

For financial systems, cryptographic approval is necessary but not sufficient. Production use also requires regulatory, operational, custody, market-access, audit and resilience controls.

## 6. Processing without exposing raw data

Where the operation permits it, prefer:
- client-side filtering and local computation;
- tokenization and selective disclosure;
- secure enclaves with remote attestation for bounded workloads;
- multiparty computation for joint calculations;
- homomorphic encryption for narrowly defined operations;
- privacy-preserving analytics and aggregate outputs.

These methods have different performance and threat-model trade-offs. They are not interchangeable and should be selected per workload. A trusted execution environment is not a substitute for key isolation, software assurance or output controls.

## 7. Current implementation boundary

The following code exists in the repair branch; it must still pass the complete CI suite and undergo independent review:

- core/secure_channel.py: AES-GCM frame confidentiality and integrity, endpoint/session binding, bounded in-process replay window. Session IDs must be fresh; replay state is not yet a distributed durable service.
- core/secure_data_plane.py: per-record AES-256-GCM envelope-encryption primitive using an injected KMS/HSM KeyProvider. It is not yet wired into the state journal, memory fabric, browser, backups or every storage adapter.
- core/authorization_replay.py: bounded local SQLite replay store with expiry and restart persistence. It is not a globally replicated, rollback-resistant authorization ledger.
- core/multiauth.py: Ed25519 threshold approvals bound to exact action statements and short expiry.
- core/trust_chain.py: identity, device, attestation, channel and expiry binding.
- core/actions.py and jarvis/core/runtime.py: fail-closed authorization; JARVIS requires an explicitly configured persistent replay database for authorized execution.

Still missing for the stated global objective:
- external production KMS/HSM adapter, tenant key hierarchy, rotation and recovery;
- encrypted integration for state journals, memory, logs, backups and every persistence boundary;
- rollback-resistant distributed replay protection and quorum/consensus;
- globally sharded data storage, replication, regional failover and tested disaster recovery;
- streaming/chunked authenticated object transport;
- production transaction ledger, idempotency/outbox and bank/exchange adapters;
- independent verification services, confidential-compute adapters and privacy-preserving computation;
- formal threat modelling, penetration testing, side-channel review, operational monitoring and compliance evidence.

## 8. Non-negotiable engineering rules

- No merge to main or the frozen architecture branch as part of this work.
- No claim of global scale, financial readiness or production security from unit tests or synthetic scenarios.
- No plaintext fallback when encryption, key management, identity, replay protection or verification is unavailable.
- No universal root key, universal administrator token or single global plaintext database.
- Every new security property must have positive, negative, replay, concurrency, restart, tampering and failure-injection tests.
- Every subsystem must document what it can prove, what it assumes and what it cannot guarantee.
