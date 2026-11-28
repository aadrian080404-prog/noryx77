# NORYX7 — Ingress Identity, Memory Isolation, Offline Delivery and Operational Trust Reconciliation

**Review date:** 2026-11-24  
**Source branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Review scope:** documentation-only, bounded source inspection. No runtime, tests, dependencies, workflow, deployment or frozen baseline modified.

## 1. Purpose and coverage

This pass extends the twelve workstreams through four cross-cutting seams:
- browser/API ingress and principal identity (W01/W08/W09);
- memory/context isolation and global memory representation (W03/W06);
- offline execution, durable delivery and uncertain side effects (W02/W08/W09);
- provider dispatch, supply-chain provenance, observability and deployment topology (W04/W05/W09/W11).

Inspected source paths include `gateway/server.py`, `gateway/auth.py`, `gateway/runtime_adapter.py`, `noryx7_operational.py`, `core/memory.py`, `core/memory_hierarchy.py`, `core/context.py`, `core/offline.py`, `core/offline_anchor.py`, `core/state_journal.py`, `core/recovery.py`, `core/egress.py`, `core/provider_router.py`, `core/provider_execution.py`, `core/resource_router.py`, `core/self_improvement.py`, `core/supply_chain.py`, `core/observability.py`, `ecosystem/global_fabric.py`, `ecosystem/runtime_dispatch.py`, `ecosystem/front_runtime.py`, `render.yaml`, and the inspected Go/Rust service entry points.

This is not a complete call-site, deployment, mobile, or external-provider audit. Findings are bounded to the inspected source snapshot.

## 2. Browser/API ingress and principal binding

### 2.1 Observed implementation

- `NoryxGateway` exposes health, bootstrap session creation and execution routes. Request bodies are capped at 16 KiB; browser input is separately capped at 8 KiB in `RuntimeAdapter`.
- `SessionAuthority` issues an HMAC-SHA256 token containing a caller-provided `client_id`, expiry and random nonce. Default TTL is one hour. Verification checks signature, expiry and non-empty client ID.
- `RuntimeAdapter` copies that client ID into task constraints as `_noryx7_client_id`; it does not itself resolve it to a cryptographically authenticated human, organization, device or workload principal.
- The bootstrap token is a shared bearer secret. The session format has no server-side session registry, explicit revocation lookup, audience/scope binding, key identifier/rotation protocol or one-time nonce consumption in the inspected implementation.
- The HTTP server documents that production must terminate TLS externally. `render.yaml` describes one Python web service; it does not deploy the inspected Go/Rust services or Android/iOS applications as a unified polyglot runtime.

### 2.2 Architectural consequence

A signed session proves possession of the signing secret and integrity of the token payload. It does not prove that a user-selected `client_id` corresponds to an enrolled principal or device. The system must not elevate a client label to identity or authorization.

The canonical ingress contract must bind:
1. enrolled principal and issuer;
2. authenticated device/workload identity and attestation state;
3. session ID, audience, issue/expiry, key ID and revocation epoch;
4. client/surface identity as metadata, not as principal proof;
5. authorized capabilities, targets, policy version and risk scope;
6. execution/request/idempotency IDs and replay state;
7. source surface, consent and data classification;
8. authenticated audit event and response correlation.

Session renewal, logout, compromise response, secret rotation and key rollover must have explicit semantics. Bootstrap credential distribution must be scoped and rate-limited, and should not be a universal credential shared across users/devices.

## 3. Memory and context isolation

### 3.1 Observed implementation

- `MemoryStore` is bounded and in-memory, validates IDs/kinds/importance, deep-copies values and can filter reads by execution ID.
- `MemoryHierarchy` is a small bounded L0–L5 key/value abstraction; its record stores only key/value/level and has no built-in source, tenant, consent, provenance, expiry or deletion tombstone.
- `ContextManager._memory_values` currently calls `memory.list()` without an execution filter and then selects items whose `source == task_id`. The stored `execution_id` is copied into the hydrated record but is not used as a filter in this method.
- Context hydration catches memory exceptions and returns an empty tuple. The resulting context does not distinguish “no matching memory” from “memory unavailable or failed”.
- `GlobalMemoryFabric` stores record metadata and payload/provenance digests, not payload bytes. Its replica requirement counts replica labels; it does not prove that replicas are distinct, healthy, reachable or independently durable.

### 3.2 Architectural requirements

Memory access must be scoped by tenant, principal, task, execution and policy, with explicit cross-execution sharing grants. Context hydration must report a typed state: complete, empty, partial, stale, denied or unavailable. Silent empty fallback can make an agent proceed with missing context while appearing fully informed.

Canonical memory records need:
- tenant/principal ownership and access policy;
- source artifact and claim lineage;
- creation/update time, validity, expiry and retention class;
- consent/legal basis and permitted purpose;
- encryption/key version and storage location;
- execution/task scope and explicit share grants;
- correction, deletion tombstone and backup/replica propagation;
- audit of reads, writes, promotion, retrieval and deletion;
- replica identity, health, durability and consistency metadata.

L0–L5 labels are placement/retention classes, not a consistency model. Promotion must not silently broaden access or retention.

## 4. Offline execution and delivery certainty

### 4.1 Observed implementation

- `OfflineSnapshot` carries principal, policy/artifact/state versions, capabilities and an integrity digest; `OfflineRuntime` also requires an injected snapshot authenticator and can use a monotonic anchor.
- `MonotonicAnchor` persists the highest snapshot epoch in SQLite WAL with FULL synchronous mode, but its own documentation calls for protected storage or hardware-backed replacement in production.
- `OfflineSyncQueue` encrypts payloads before storing them, verifies payload/ciphertext digests and supports idempotent enqueue by execution ID.
- The inspected queue is an in-memory dictionary, not a durable outbox. Its sequence counter and pending envelopes do not survive process restart.
- `OfflineRuntime.execute` enqueues before guarded execution. On any exception it acknowledges/removes the queued envelope and moves to RECOVERY. If an external side effect occurred before an exception, this cleanup can discard the only local delivery record while the effect remains uncertain.
- `acknowledge_synced` removes records after remote acknowledgement; conflict handling is explicit, but durable remote reconciliation and indeterminate outcomes are not supplied by the in-memory queue.

### 4.2 Required delivery state machine

Offline work must distinguish:
- NOT_STARTED;
- ADMITTED;
- INTENT_DURABLE;
- DISPATCHED;
- EFFECT_CONFIRMED;
- EFFECT_REJECTED;
- EFFECT_INDETERMINATE;
- SYNC_PENDING;
- REMOTE_RECONCILED;
- CONFLICT / COMPENSATION_REQUIRED.

A failure after dispatch must never be translated automatically into “no effect”. Preserve the intent and receipt, query provider/device state using the idempotency key, reconcile with authenticated evidence, and require compensation or human review when certainty cannot be established.

The durable outbox must survive process/device restart, use transactional sequence allocation, protect against duplicate delivery, and retain a signed dispatch/acknowledgement chain. Local commit, journal append, outbox update and external side effect need an explicit transaction/compensation boundary; SQLite transactionality within one database does not make external effects atomic.

## 5. Egress, provider routing and resource placement

### 5.1 Observed implementation

- `EgressPolicy` is a bounded in-memory allowlist keyed by component, host, port and protocol. It canonicalizes literal IP addresses and host strings, but does not itself resolve DNS, pin the resolved address, validate redirects, mediate sockets or prove every outbound path consults it.
- `ProviderRouter` deterministically chooses the first registered provider for a capability and can retry another provider after any exception. It does not distinguish transient errors from an indeterminate external side effect.
- `ProviderExecutionGateway` performs an injected authorization callback immediately before dispatch through `ExecutionFabric`, but its generated action ID is deterministic from principal/provider/capability rather than a unique per-attempt idempotency key.
- `ResourceRouter` selects DEVICE/EDGE/CLOUD from static complexity/privacy/latency thresholds. It has no live capacity, jurisdiction, residency, cost, energy or provider-health input.

### 5.2 Required contracts

Separate provider discovery, capability qualification, policy authorization, placement, dispatch and result reconciliation. Failover is safe only when the prior attempt is known not to have taken effect or when the downstream operation is idempotent and reconciled. An arbitrary exception must not automatically trigger a second payment/booking/transaction.

Each provider invocation needs unique intent ID, idempotency key, request digest, scoped principal, target, quote/amount constraints, timeout, cancellation semantics, signed receipt and final reconciliation state. Resource placement needs hard residency/privacy constraints before optimization and live capacity/cost/energy/health data with explicit degraded-mode behavior.

## 6. Recovery, state journal and protected anchors

- `StateJournal` provides SQLite WAL/FULL transactional append, unique execution IDs, sequence continuity and record digest verification.
- A SHA-256 digest detects accidental/tampered record changes only if the expected digest/root is protected; the inspected record digest is stored alongside the record in the same database. It is not an external signature or hardware trust root.
- `RecoveryController.run_if_normal` serializes a bounded critical operation against local recovery transitions using one in-process lock. This does not coordinate separate processes, nodes, databases or external systems.
- State journal, offline anchor, runtime journal and external side-effect receipts remain separate durability domains. Their cross-store epoch and transaction protocol is still an architecture decision.

Define one recovery authority/epoch model across principal revocation, session revocation, authorization, state journal, offline snapshot, key lifecycle and device trust. Specify monotonicity, restart recovery, replica consensus and behavior under partial network partitions.

## 7. Supply chain, self-improvement and security observability

- `SupplyChainVerifier` validates an Ed25519 signature from a configured trusted-key set and checks artifact bytes against a SHA-256 digest. This is a useful integrity primitive.
- The inspected contract does not itself provide SBOM, build provenance, reproducible build, dependency policy, vulnerability disposition, signer role authorization, key rotation/revocation, release approval or staged deployment promotion.
- `ImprovementPipeline` enforces an in-process stage order OBSERVE→ANALYZE→PROPOSE→SIMULATE→TEST→VERIFY→ADMITTED. `admit_external` is a boundary method, not proof of an independent reviewer, protected release signer, immutable approval record or rollback mechanism.
- `SecurityEventBus` is a bounded in-memory append-only list. It is not a durable, remote, tamper-evident incident ledger and has no built-in alert ownership or containment orchestration.

A production release needs signed source/build provenance, SBOM, artifact attestations, independent approvals, policy evaluation, staged rollout, health gates, rollback/rollback inhibition, key compromise handling and retained audit evidence. Security events need durable protected storage, trusted timestamps, event correlation, alert acknowledgement, incident ownership, escalation, containment authorization and post-incident evidence retention.

## 8. Deployment and polyglot boundary

The inspected Render manifest declares a single Python service started with Uvicorn and three externally supplied secrets. The inspected Go service exposes a health endpoint and SHA-256 digest endpoint; the Rust library defines an execution envelope digest and a deny-by-default helper. These are not evidence that Go/Rust services are integrated with the Python gateway or deployed as one authenticated system. Mobile surfaces require their own enrollment, credential, revocation and update contracts.

The release architecture must define:
- authoritative service inventory and ownership;
- service-to-service identities and mutual authentication;
- API/schema compatibility and version negotiation;
- secrets injection/rotation and zeroization;
- TLS/certificate lifecycle and trusted proxy headers;
- readiness/liveness/dependency health distinctions;
- capacity, scaling, rate limits and backpressure;
- logs/metrics/traces with privacy-preserving correlation IDs;
- backup/restore, disaster recovery and regional failover;
- staged release, canary, rollback and decommission;
- Android/iOS/browser release and attestation lifecycle.

## 9. Cross-workstream consequences

| Workstream | New source-backed consequence |
|---|---|
| W01 Identity | Browser client ID is not an authenticated principal; define enrollment, issuer, session revocation, scope and device binding |
| W02 Runtime | Durable outbox and cross-store state/side-effect certainty remain unresolved |
| W03 Memory | Context hydration currently ignores execution_id filtering and hides memory errors as empty context; define tenant/consent/expiry/deletion |
| W04 Agents | Provider failover must distinguish retry-safe errors from uncertain effects; role and principal scopes must travel with dispatch |
| W05 Routing | Static resource tiers need residency, live capacity, cost, energy and provider-health constraints |
| W06 Evidence | Durable source/effect receipts must join claim/evidence lineage and audit |
| W07 MIRROR WORLD | Offline sensor/device actuation requires calibrated model and non-actuating default, not merely offline capability |
| W08 Surfaces | Browser, Android, iOS and offline sessions need one canonical enrollment and revocation contract |
| W09 Security | Egress allowlist must be enforced at socket/DNS/redirect boundary; release keys and audit roots need protected lifecycle |
| W10 Domains | Specialist outputs and provider calls must retain qualified scope and provenance through gateway/context |
| W11 Operations | Single Python Render service is not polyglot production topology; define SLO, telemetry, backup, incident and release gates |
| W12 Governance | Offline/community work requires durable participant identity, consent, compensation, incident/safety and project evidence records |

## 10. Proposed architecture decisions (OPEN)

### ADR-B102 — Canonical Ingress Principal and Session Lifecycle
Bind session tokens to enrolled principal, issuer, device/workload, audience, scope, key ID, expiry, revocation epoch and execution correlation. Client IDs remain labels, never identity proof.

### ADR-B103 — Memory Context Isolation and Degraded-State Semantics
Define tenant/principal/task/execution scoping, explicit sharing grants, typed hydration outcomes, provenance, consent, expiry, deletion propagation and audit. A failed memory read must not silently masquerade as an empty context.

### ADR-B104 — Durable Offline Outbox and Indeterminate Side-Effect Reconciliation
Define persistent intent/outbox/receipt state, unique idempotency, crash recovery, duplicate delivery, indeterminate outcomes, compensation and remote acknowledgement. Never discard a dispatch record merely because local execution raised an exception.

### ADR-B105 — Durable Security Event and Incident Lifecycle
Define protected append-only event custody, trusted time, correlation, alert ownership, escalation, containment authorization, retention and post-incident review.

### ADR-B106 — Evidence-Backed Release and Self-Improvement Admission
Bind source/build provenance, SBOM, artifact digest/signature, independent review, policy gates, staged rollout, rollback and key lifecycle. An in-process VERIFY stage is not independent production admission.

These proposals extend prior B70, B72–B74, B78, B79–B82, B86, B98 and related contracts. They must be reconciled before acceptance.

## 11. Closure status

W01–W12 remain PARTIAL. This pass adds concrete source findings and architecture decisions, but does not implement fixes, complete call-site tracing, certify deployment, run tests, integrate polyglot services or freeze the architecture.
