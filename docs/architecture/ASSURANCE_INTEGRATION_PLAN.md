# NORYX7 — assurance and integration work plan

Status: engineering plan; no production-readiness claim.
Baseline inspected: `main` on 2026-11-17. This document does not change runtime behavior.

## Operating rules

1. Never modify the frozen architecture reference or push directly to `main`.
2. Implement each bounded workstream on an isolated branch and draft PR.
3. A capability is not operational merely because its class exists or unit tests pass.
4. Every PR must identify its exact base/head SHA, changed contracts, threat model, tests, limitations and rollback path.
5. Preserve deny-by-default behavior. If a dependency, identity, clock, storage layer or verifier is unavailable, fail closed.
6. Do not claim a mathematical guarantee beyond the assumptions and system boundary actually modeled.

## Baseline findings confirmed in source

- `core/offline.py` already defines offline snapshots, authenticated snapshot admission, an encrypted bounded outbox, replay/idempotency handling in its in-memory queue, a monotonic-anchor interface and recovery-aware execution. Do not create a second offline subsystem. First establish which state and queue components are durable across process/device restart.
- `core/state_journal.py` already provides SQLite WAL persistence, FULL synchronous mode, append-only state commits, per-record SHA-256 digests and sequence-gap checks. This is useful integrity detection, but a plain digest is not an external trust anchor and does not by itself prevent a valid older database snapshot from being restored.
- `core/audit.py` already provides an in-memory hash chain and authenticated checkpoints through a KeyProvider. The event chain itself is not durable in this implementation; checkpoint creation is not the same as persisting and independently anchoring the event stream.
- `core/actions.py` binds one-shot grants to an action, execution, principal key fingerprint, nonce and expiry. Its consumed-nonce set is process-local, so it cannot alone guarantee one-time use across processes, devices or restarts.
- `core/verification.py` checks output presence and structural result contracts. Presence is not semantic correctness; the caller must supply an independent, task-specific verifier before treating an output as verified.
- `core/memory.py` bounds item count and isolates reads by execution ID, but does not impose a byte budget or durable multi-device replication contract.
- `noryx7_runtime/model_fabric.py` already supports capability-based model selection with expected cost and latency, plus request/result provenance binding. Routing estimates need observed telemetry and calibrated quality evidence before they can be treated as performance guarantees.
- `core/runtime.py` wires together policy, identity, offline runtime, state journal, memory, router, HYPERSYNTH and audit. Integration should extend these canonical components rather than create parallel registries.

## Parallel workstreams

### W0 — Baseline and regression control
- Record repository/branch/commit identities and preserve the frozen reference.
- Inventory tests and workflows before changing runtime code.
- Add a change-impact map for shared contracts and import dependencies.
- Acceptance: reproducible baseline test run and exact SHA recorded; no unexplained test regressions.

### W1 — Identity, keys and authorization
- Separate declared identity, cryptographically verified identity, trusted identity and operation authority.
- Persist device identity through a protected keystore; never silently regenerate a durable identity after restart.
- Replace process-local nonce consumption with a transactional replay ledger whose uniqueness constraint is enforced at the authoritative target.
- Define revocation epochs and behavior during offline partitions.
- Acceptance: concurrent duplicate-consumption tests, restart tests, revocation races, wrong-principal and wrong-target tests; at most one successful consumption per grant at the authority boundary.

### W2 — Execution supervisor and recovery
- Model execution as durable states: PROPOSED, RESERVED, STARTED, EXECUTED, VERIFIED, COMMITTED, REJECTED, UNKNOWN.
- Give every operation a stable operation ID, target generation and idempotency key.
- Use an atomic compare-generation-and-start boundary at the actual target/supervisor; do not hold a database transaction across arbitrary external execution.
- On crash, reconcile UNKNOWN operations; never blindly repeat a non-idempotent action.
- Acceptance: crash injection at every transition, revocation/start races, stale generation rejection and duplicate delivery tests.

### W3 — Verification and proof-carrying execution
- Keep structural validation separate from semantic/task-specific verification.
- Require verifier identity, verifier version, input/output digests, policy version and evidence references.
- A model-generated confidence score is not proof and must not independently authorize commit.
- Acceptance: malformed, empty, contradictory, stale and adversarial outputs are rejected; valid outputs pass only the declared task verifier.

### W4 — Durable audit and state integrity
- Persist audit events before acknowledging critical transitions.
- Add sequence numbers, canonical encoding, schema versions, key rotation and independently stored checkpoints.
- Detect truncation, reordering, tampering and rollback to an older valid database snapshot; document the limits of local-only anchoring.
- Acceptance: tamper, truncate, reorder, rollback, key-rotation and crash-recovery tests.

### W5 — Memory and causal provenance
- Retain execution isolation; add byte-based quotas, per-principal access policy, retention/expiry and deletion semantics.
- Represent provenance as a directed acyclic event graph; reject cycles and missing parents.
- Keep sensitive payloads out of audit records; store references/digests where possible.
- Acceptance: cross-tenant isolation, quota exhaustion, expiry, deletion and causal-chain reconstruction tests.

### W6 — Model Fabric and resource intelligence
- Reuse the existing Model Fabric and provider bridge.
- Add observed latency/cost/error/quality telemetry with bounded windows and privacy-aware aggregation.
- Route by hard constraints first (privacy, capability, policy, budget), then optimize quality/cost/latency/energy.
- Use deterministic fallback for tasks with deterministic solutions; avoid multi-model fan-out unless expected value exceeds its cost.
- Acceptance: routing reproducibility, budget enforcement, stale telemetry fallback, provider outage and no-capability cases.

### W7 — Distributed device fabric
- Classify state before selecting replication: CRDT only for mergeable state; transactional authority for one-time grants, money and exclusive actions.
- Add bounded gossip, authenticated membership, replay protection, backpressure and offline reconciliation.
- Treat node reputation as advisory, never as a substitute for cryptographic identity or authorization.
- Acceptance: partition, delayed/duplicate message, Byzantine input, resource exhaustion and convergence tests for each declared CRDT.

### W8 — Performance and efficiency
- Establish p50/p95/p99 latency, memory, CPU, energy, network bytes and cost baselines.
- Add event-driven activation, bounded queues, cancellation, backpressure, caching with versioned keys and incremental verification.
- Parallelize only independent DAG nodes; include synchronization and verification overhead in benchmarks.
- Acceptance: benchmark comparison against baseline with no security invariant weakened.

### W9 — Multimodal understanding and Systems Understanding/Reverse Engineering
- Normalize text, audio, gesture, geometry and symbolic input into a typed canonical intent representation.
- Treat cross-modal agreement as corroboration, not identity proof or execution authority.
- Run static/dynamic analysis only in an isolated, resource-bounded sandbox with explicit authorization and provenance.
- Acceptance: ambiguity tests, contradictory modality tests, prompt-injection tests, sandbox escape tests and resource-limit tests.

### W10 — Advanced cryptography and hardware
- Stage post-quantum migration behind algorithm-agile interfaces and interoperability tests.
- Evaluate ZKP, MPC/FHE and hardware roots of trust only against measured threat models, hardware support and cost.
- Do not assume PUFs are unclonable, ZKPs are cheap, or QKD is a universal replacement for authenticated classical cryptography.
- Acceptance: threat model, independent implementation review, benchmark and fallback plan before production use.

### W11 — Edge/PSP/console targets
- Start with supported user-space applications and small deterministic node services.
- Keep heavyweight inference on capable nodes; low-resource devices provide queueing, UI, sensors and bounded coordination.
- Use only official/authorized console development paths.
- Acceptance: per-device resource envelope, reproducible build, hardware test and signed capability manifest.

## Cross-cutting release gate

A feature may be marked:
- SPECIFIED — contract and threat model documented;
- IMPLEMENTED — code exists;
- TESTED — relevant automated tests pass on the exact commit;
- DEVICE-VALIDATED — tested on named hardware/software versions;
- OPERATIONAL — dependencies, keys, policies, monitoring, recovery and rollback are configured and independently checked.

These states are not interchangeable. A green CI run does not by itself establish DEVICE-VALIDATED or OPERATIONAL status.

## Immediate implementation order

Run W0 first, then develop W1–W6 in parallel only where shared interfaces are frozen. W2/W1/W4 must agree on the operation ID, generation, authorization-consumption and audit-commit protocol before implementation is integrated. W5/W6/W7/W8/W9 can proceed against versioned contracts. W10/W11 remain experimental until the core assurance gates are met.

## Explicit non-goals

- No direct push to `main`.
- No merge or deployment from this work plan.
- No claim of perfect security, semantic correctness or unlimited scalability.
- No duplicate identity, memory, model-routing, offline or audit subsystem.
