# Runtime durable trust bootstrap contract v1

Status: integration contract; implementation is not yet claimed complete.

This contract defines how the runtime must compose the durable identity and replay primitives without turning persistence into implicit authority.

## Required startup order

1. Load configuration from an explicitly selected deployment profile. Reject missing, ambiguous, or writable-by-untrusted-user database/key paths.
2. Open the durable agent identity registry and principal-agent binding registry against the intended trust database. Verify schema/version and fail closed on migration or integrity errors.
3. Obtain private-key operations through a caller-supplied key provider (KMS/HSM or isolated OS keystore adapter). The SQLite registry stores public keys and trust metadata only; it must never become a private-key store.
4. Resolve the active principal-agent binding and verify both identities are live. A valid agent key alone does not establish principal ownership.
5. Open the durable authorization replay guard. Capacity/configuration mismatch, database lock/integrity failure, or inability to reserve a replay token aborts privileged startup or action verification.
6. Construct TrustChain with the durable identity trust adapter and ReplayGuard protocol implementation. No silent fallback to in-memory replay protection is allowed in a durable deployment profile.
7. Construct ActionGate and local audit sink. Privileged execution remains disabled until both are healthy and their policy versions are loaded.
8. Mark runtime READY only after every required component has passed self-check. Any partial failure leaves the runtime ISOLATED/NOT_READY.

## Dependency and authority rules

- PrincipalIdentity, AgentIdentity, DeviceIdentity, and ExecutionIdentity are distinct namespaces.
- Principal-agent binding is checked against the live durable binding registry on each authorization boundary; cached admission is not permanent authority.
- Identity generation is monotonic within the registry. Rotation requires proof from both old and new Ed25519 keys and an expected-generation compare-and-swap.
- Revocation is terminal for the agent identifier. Re-enrollment uses a new identifier and an independently authorized procedure.
- A signed federation envelope, imported memory item, quorum signal, or stigmergic trace is evidence/data, never an ActionGate grant.
- Every action derived from imported or recalled memory is re-authorized locally and audited locally.
- Replay consumption is atomic and precedes the side effect. If audit persistence fails, execution is denied. If the side effect fails after token consumption, the token remains consumed.
- Do not silently downgrade to ephemeral keys, in-memory replay guards, permissive trust callbacks, or disabled audit.

## Rollback and distributed deployment boundary

SQLite transactions and generation checks protect concurrent writers sharing the same database. They do not prove freshness after an attacker restores an older database snapshot, nor do they provide consensus across independent hosts.

A production multi-host profile therefore requires an external monotonic witness (or equivalent hardware-backed monotonic state) for identity generations, revocation epochs, replay reclamation epochs, and recovery epochs. Until that dependency exists, the supported durable profile is single-database/single-trust-domain; multi-host privileged execution must remain disabled or use a separately proven consensus service.

## Required integration tests

- Restart: the same configured identity remains trusted; a different key under the same agent ID is rejected.
- Rotation: old+new signatures and expected generation are required; stale concurrent rotations have exactly one winner.
- Revocation: restart does not restore a revoked identity; dependent principal-agent bindings cannot authorize it.
- Key provider: missing provider, wrong public/private pairing, unavailable KMS/HSM, and key rotation failure all leave runtime not ready.
- Replay: two independent guard instances sharing one database accept a token exactly once; restart does not reset consumption.
- Configuration: durable mode cannot silently instantiate in-memory defaults; incompatible DB paths/capacities fail closed.
- Audit/ActionGate: audit outage blocks the action; memory import alone cannot execute; revoked principal/agent is rejected immediately.
- Recovery: restored stale database state is rejected when the external monotonic witness is enabled; without that witness, deployment is explicitly classified as rollback-unprotected.
- Readiness: no privileged route is exposed before all dependencies pass self-check.

## Acceptance gate

This contract is satisfied only by runtime wiring plus automated tests exercising real SQLite files, two independently constructed runtime instances, restart, revocation, and failure injection. Unit tests of individual registries alone are insufficient.

No merge, deployment, or claim of production readiness follows from adding this contract.
