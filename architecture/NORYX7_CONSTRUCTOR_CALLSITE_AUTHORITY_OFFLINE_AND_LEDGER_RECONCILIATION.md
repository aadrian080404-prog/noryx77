# NORYX7 — Constructor, Call-Site, Authority, Offline and Ledger Reconciliation

**Date:** 2026-11-25  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source HEAD inspected:** `f042c11008eb95333260d06982f05ee1c2479ad2`  
**Disposition:** architecture-only source mapping. No runtime, tests, workflows, dependencies, deployment or configuration changed. No tests were executed in this pass.

## 1. Method and scope boundary

This pass follows the prior W01–W12 synthesis with a deeper inspection of exact source files, selected integration tests, and the complete recursive Git tree (471 tracked blobs; tree response not truncated). The source paths below were fetched at the inspected branch HEAD and their blob SHAs recorded. A repository tree proves path existence, not complete call-site coverage. GitHub code search returned empty/incomplete results for some exact symbol searches, so empty search results are not used as evidence that a symbol has no consumers. The constructor/call-site map below is deliberately bounded to directly inspected files and test references.

## 2. New source anchors

| Path | Blob SHA | Observed role |
|---|---|---|
| `core/actions.py` | `5e2fc212abea2873bb471b12e6fe6f5021664e97` | AuthorizationGrant, AuthorizationAuthority, ActionGate |
| `core/policy.py` | `e8beea32349bc6ca17acc53dbbf6593439ea976b` | Default-deny PolicyEngine; named internal capability routes |
| `core/security.py` | `6d2962db7835d23cbf44af130be492864aae9652` | SecurityBoundary and recovery/risk/policy checks |
| `core/security_integration.py` | `8a681ac6e73b0ef0dd49fdeaa7416571f132b563` | DefenseGate envelope boundary; does not execute actions |
| `core/execution_fabric.py` | `fd14d2c3b1ab9fb70d500d09adfaf3e55e91b796` | Explicit adapter registration and authorization callback |
| `core/offline_adapters.py` | `bcdd8210b71f60a5f07f50b8975798fdd8c6b6f3` | Policy, verification and authenticated-cipher adapters |
| `core/offline_anchor.py` | `a130043ae7dff949b072ae97fd00137d8051d2ea` | SQLite monotonic snapshot anchor |
| `noryx7_runtime/attestation.py` | `b417bdb09f5ad920f7b6cf96910aea5c6447ac2a` | Ed25519 signer/verifier, identity-bound and chain verifiers |
| `noryx7_runtime/recovery.py` | `ecd5743a494a150e13556e5c3932b77a6b08aaa7` | Runtime journal recovery with attestation and optional identity registry |
| `gateway/auth.py` | `fa456172c99b183dcb2acd0ec99303ec540d2583` | SessionAuthority |
| `gateway/server.py` | `b434cdbe118ecea48029adcd2c954fa1ac14461c` | Standalone HTTP gateway and Bearer session check |
| `gateway/runtime_adapter.py` | `6661fbc150c77ba79d3b1f16cc0f66742b20f935` | RuntimeAdapter wrapper |
| `web/app.py` | `a03d012d6f9f2fdbfb8a5e64397511e5ac692360` | FastAPI ingress routes |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` | Typed DispatchReceipt and digest constructor |
| `jarvis/security/authorization.py` | `dd7db5e133632061bbfbac88ed47bede27bc387c` | Separate in-memory principal/capability/target grant set |
| `core/test_authorization_grants.py` | `239b0b69a872ca362d0eba7f68f841442ecfb73a` | Tests for exact action/execution/target/parameters/risk and expiry/signature |
| `core/test_authorization_replay.py` | `ebc11298a2635cf90f1eb4a632b63d1b77937bd3` | Bounded single-use replay guard tests |
| `core/test_identity_boundaries.py` | `ac4b71b0ed54b16b681589758e74e32f8e2f0144` | Identity trust/revocation and execution-binding tests |
| `core/test_state_journal_integration.py` | `3f16420b2470176d0db550f9b76e700d029bb38f` | StateStore durable journal rehydration test |
| `core/test_coordination_boundaries.py` | `5bcee330d77ddc32f07c30c259e9c4012829e3d3` | Coordinator identity, revocation and task binding tests |
| `tests/test_recovery_atomicity.py` | `2a54a45acf73c113011bc49505d4d27a094595af` | RecoveryController serialization and stale epoch tests |
| `tests/test_recovery_canonical.py` | `2bd01b1cf1ae38caeb98cd2970d18eaf9cf365f0` | JARVIS/canonical recovery type identity test |
| `tests/test_offline.py` | `8a2ba74127f2666bb5dda32af64fbbb12d4800cb` | Offline admission, encrypted queue, reconnect/conflict tests |
| `tests/test_offline_anchor.py` | `d8d51aff3ee5cea972cb2c12e24d755785ab58c8` | Monotonic anchor restart/rollback test |
| `tests/test_runtime_identity_binding.py` | `d7bc7951f719df78b9e1aa9a64c24a42fa5b02a2` | StateCommit identity fingerprint binding test |
| `tests/test_recovery_atomicity.py` | `2a54a45acf73c113011bc49505d4d27a094595af` | Canonical recovery transition synchronization |
| `architecture/ADR-003-CANONICAL-STATE-JOURNAL-AND-RECOVERY.md` | `85560c09b7a43b93e157eb81ac1ce79e75a71c21` | Canonical state/recovery ADR; acceptance remains pending |
| `architecture/NORYX7_AGENT_EVIDENCE_MIRROR_WORLD_AND_GLOBAL_IMPACT_RECONCILIATION.md` | `e2ee98e058fe2a27f05d8f1d3b98c78403937c18` | Agent/evidence/impact architecture and W12 fund separation |
| `architecture/BUSINESS_PROJECT_FABRIC.md` | `30297c96c506553f8b8b94dd57c297b8b3b096ca` | Project, commission, accounting and financial boundary model |

## 3. W01/W09 — identity, grants, replay and revocation

### 3.1 Stronger grant semantics are already present

`core/actions.py` defines:
- `AuthorizationGrant`, a one-shot grant;
- `AuthorizationAuthority`, an issuer/verifier with a minimum 32-byte secret and bounded TTL;
- canonical action-parameter fingerprinting before grant issuance;
- binding to action ID/type/target, execution ID, principal ID and principal public-key fingerprint;
- nonce/signature/expiry checks;
- a bounded in-process used-nonce set;
- `consume_and_execute`, which locks the identity registry, checks current trust, consumes the nonce and calls the executor while holding the registry lock;
- `ActionGate`, a final fail-closed policy/security/limits boundary.

The grant tests explicitly cover cross-execution, action ID, target, parameters, risk class, noncanonical parameters, expiry, signature tampering, missing grants and short secrets. Identity boundary tests cover revocation before routing/coordinator execution and result admission.

**Interpretation:** the architecture must preserve these specific properties. It would be inaccurate to say the repository has no action-target binding or no revocation-aware one-shot authorization.

### 3.2 Remaining authority questions

The `AuthorizationAuthority` used-nonce set is in-process. The separately inspected `AuthorizationReplayGuard` is also bounded/in-process. The identity registry is passed optionally to the authority. The action grant's issuer secret, registry lifecycle, persistence, cross-process replay scope, multi-replica uniqueness, key rotation and revocation freshness still need constructor and deployment mapping.

`jarvis/security/authorization.py` is another simple in-memory grant set keyed by principal/capability/target. Its equivalence to `core.actions.AuthorizationAuthority` is not established. `core/security_integration.DefenseGate` is a separate decision boundary that explicitly does not execute actions. These should not be collapsed by name alone.

**Closure target:** one authority graph with typed issuer, subject, audience, capability, target, execution, policy version, expiry, revocation epoch and replay namespace. Each local gate must identify whether it is issuer, verifier, projection or enforcement point.

## 4. W02/W03 — state journals and recovery

### 4.1 Two journal domains are distinct by type and semantics

- `noryx7_runtime.state.StateJournal`: in-memory runtime reservation/attestation journal; `RuntimeEngine` consumes it. `noryx7_runtime.recovery.RuntimeRecovery` requires this exact journal type, validates sequence, step uniqueness, runtime ID, identity/key fingerprint, action/output digests, signatures and attestation chain.
- `core.state_journal.StateJournal`: SQLite append-only verified StateCommit journal. It enables WAL, synchronous FULL and foreign keys; stores canonical state JSON, principal ID/key fingerprint, verification stage, sequence and digest; uses BEGIN IMMEDIATE/COMMIT/ROLLBACK; recovers contiguous sequence and validates digests.
- `core.state.StateStore` optionally accepts the SQLite journal and has an integration test that reopens the DB and rehydrates a commit.
- `core.recovery.RecoveryController` serializes normal operations against recovery transitions and increments an epoch; tests verify transition serialization and stale epoch rejection.

The tests establish intended behavior but were not executed in this architecture pass.

### 4.2 ADR-003 status

ADR-003 describes a canonical journal/recovery model, but it is not proof the two source journals have been unified. The document itself notes that reservation-before-dispatch is not a crash-safe global guarantee until backend durability, namespace, atomicity and recovery are settled.

**Closure target:** retain distinct record types if their responsibilities differ, but define a canonical transaction protocol across reservation, dispatch, effect receipt, attestation, verified state commit and recovery. Identify whether a durable reservation journal exists, where it is constructed, and which runtime paths use it. Do not rename or merge journal classes until call-site evidence proves safe equivalence.

## 5. W08 — offline: durable anti-rollback is not durable outbox

### 5.1 Confirmed positive controls

`core/offline.py` defines a bounded encrypted outbox. It verifies payload digest, encrypts payload with execution-specific AAD, tracks a monotonic in-process sequence and rejects duplicate execution IDs with changed content. Offline admission validates snapshot integrity/authenticator, age, principal, capability, policy, recovery state/epoch and result verifier. Reconnect requires authenticated/verified synchronization and detects remote state-version conflicts. Tests cover encrypted queue, duplicate idempotency, tampered/stale snapshots, rollback, conflicts and reconnect.

`core/offline_anchor.py` provides a separate SQLite monotonic anchor. It uses WAL and synchronous FULL and transactionally persists the highest accepted snapshot epoch/ID; a test checks restart persistence and rollback rejection.

`core/offline_adapters.py` includes adapters for policy, verification and a key-ID-bound authenticated cipher.

### 5.2 Remaining persistence and acknowledgement gap

Despite the durable anchor, `OfflineSyncQueue` stores `_records` and `_sequence` in memory. `OfflineRuntime` constructs this queue internally. The queue's `acknowledge(execution_id)` removes the item from memory. The offline runtime also has a `acknowledge_synced` path, but a durable outbox/inbox adapter and atomic remote acknowledgement protocol are not established by the inspected files.

The offline execute path can transition to RECOVERY on exceptions. If a local effect occurred before a later exception, a durable effect reconciliation record is not established by this bounded inspection.

**Closure target:** persistent encrypted outbox, crash-safe sequence allocation, signed remote receipt, idempotent inbox, ack-before-delete, uncertain local-effect reconciliation, key rotation and backup/deletion policy. The monotonic snapshot anchor and the queue must remain separate records with separate durability claims.

## 6. W02/W05/W11 — ingress, adapters and provider retry

### 6.1 Ingress distinction

`web/app.py` registers `/v1/session`, `/v1/execute` and `/api/chat`. The first issues a session; the second validates Bearer token through the gateway session authority; the chat route directly calls runtime. `gateway/server.py` provides a separate HTTP server with a Bearer check. `gateway/runtime_adapter.py` wraps an operational runtime.

This proves distinct application code paths, not an externally reachable vulnerability. Reverse proxy, ASGI middleware, deployment exposure, network policy and browser-origin protections must be traced separately.

### 6.2 Execution adapters

`core/execution_fabric.py` requires an authorization callback at construction and uses explicit adapter registration. This is a positive local boundary. It does not by itself prove that every external dispatch route is mediated by the same ActionGate or authority.

ProviderRouter, ProviderExecutionGateway and ResilientProviderExecutor remain distinct from the ExecutionFabric registration boundary. A full consumer/constructor graph is still open, particularly nested retries and the exact adapter selected for each external provider.

**Closure target:** one ingress trust policy and one effect-aware dispatch coordinator, with explicit adapter registration, principal propagation, target identity, idempotency key, dispatch attempt and target receipt. Keep route-local and upstream controls separately evidenced.

## 7. W04 — agent coordinator and identity boundaries

`core/coordination.py` creates an ActionGate if none is supplied, using PolicyEngine, SecurityBoundary and RuntimeLimits. It checks agent identity against router-provided registry where available, binds tasks/results to execution identity, and validates trusted agents and consensus results. Tests cover forged identity, wrong verification stage, duplicate agent identity, unknown/revoked agents, revocation during execution and cross-execution task identity.

The previously documented `AgentMesh` role-only lexical selection remains a routing abstraction, not an authority or qualification system. The tests and coordinator boundaries do not prove complete domain qualification, resource scheduling or independent verification.

**Closure target:** explicit injected shared ActionGate/AuthorizationAuthority/IdentityRegistry ownership; parent execution ID propagation; qualified capability-aware routing; true DAG scheduling; independent verifier identity and conflict checks; cancellation/partial-join semantics.

## 8. W06/W07/W10 — evidence, simulation and specialist assurance

The source includes Ed25519 attestation signer/verifier, identity-bound verifier and attestation-chain verifier. Runtime recovery checks the attestation chain against optional trusted identity registry. This is stronger than a plain hash-only log, but signatures establish scoped origin/integrity, not the truth of a claim or the real-world effect.

The existing evidence/MIRROR WORLD reconciliation distinguishes agent execution, evidence admission, synthetic simulation and impact claims. Qualification still needs a source-backed credential authority, scope, jurisdiction, currency, expiry, suspension, conflicts and independent reviewer lineage. A domain catalog or signed agent identity is not qualification.

**Closure target:** one evidence custody graph joining source acquisition, claim, signer, verifier, calibration, simulation manifest, field observation and admission decision. Keep simulation-to-reality admission separate and explicitly authorized.

## 9. W12 — financial, marketplace and public-impact boundary

The recursive tree and bounded source pass found the architecture definitions in `BUSINESS_PROJECT_FABRIC.md` and the agent/evidence/impact reconciliation. They specify separate customer funds, third-party funds and company revenue/commissions; deterministic auditable commission rules; authorized transaction adapters; explicit consent, beneficiary/purpose validation, limits, disputes and audit; models/agents may propose but not move funds.

This pass did **not** establish a complete source-backed production ledger/payment/escrow implementation or an independently audited impact measurement pipeline. This is a bounded finding, not a universal absence claim: a deeper search for all financial adapters, provider integrations and persistence paths is still required.

**Closure target:** double-entry journal invariants, append-only entries, fund segregation, custody/escrow, idempotent payment intents, settlement/reversal/dispute lifecycle, authorization independent of model output, reconciliation, and impact evidence with baseline/counterfactual/additionality/leakage/rebound/permanence, uncertainty, verifier independence and appeal.

## 10. Constructor/call-site evidence matrix

| Component | Directly observed construction/use | Open mapping |
|---|---|---|
| IdentityRegistry | Tests instantiate; RuntimeRecovery accepts optional instance; AuthorizationAuthority accepts optional registry | All production constructors, singleton/DI registration, revocation writer/readers |
| AuthorizationAuthority | Constructed in grant tests; optional registry injected | Production issuer, secret source/rotation, all consumers and replica scope |
| ActionGate | Coordinator can construct default; grant tests inject authority | All gate instances and whether same authority/policy/recovery is shared |
| AuthorizationReplayGuard | RuntimeEngine constructs a guard; tests instantiate | All other guards, persistence, shared namespace and process scope |
| Runtime StateJournal | RuntimeEngine owns/injects runtime journal; RuntimeRecovery requires same type | All runtime construction paths, durable adapter and recovery wiring |
| Core StateJournal | StateStore accepts optional journal; integration test reopens SQLite | Production construction path, path/key permissions, backup and migration |
| RecoveryController | Unit tests; JARVIS canonical alias test | Runtime-wide owner and exact injection into all action/offline boundaries |
| OfflineRuntime | Test factory constructs with adapters; constructor creates in-memory OfflineSyncQueue | Production factory, persistent queue adapter, anchor injection, process restart semantics |
| ProviderRouter | ProviderExecutionGateway/ResilientProviderExecutor default to new router when none supplied | All provider constructors, router sharing, retry nesting |
| AgentCoordinator | Tests construct with routers/verifiers and optional gate | Production coordinator factory, all task sources, parent ID propagation |
| DispatchReceipt | runtime dispatch uses typed receipt factory | All dispatch fronts, evidence semantics and target-effect proof |

## 11. Updated cross-workstream decisions and closure conditions

1. Keep identity registries, session authorities, authorization issuers, and enforcement gates distinct until their issuer/projection relationships are evidenced.
2. Preserve exact grant binding and atomic consume/execute properties already implemented; extend durability and distributed replay semantics without weakening them.
3. Keep runtime reservation/attestation journal and verified-state commit journal distinct unless a proven adapter/transaction contract unifies them.
4. Treat ADR-003 as proposed architectural direction, not accepted implementation.
5. Separate durable offline monotonic anchor from volatile encrypted outbox. Define persistent queue, acknowledgement, remote inbox and uncertain-effect recovery.
6. Keep each ingress route's local authentication and upstream proxy controls separately mapped.
7. Treat dispatch receipt as an authenticated structural receipt, not proof of target-side effect unless it binds a target-generated receipt.
8. Keep provider retries under one effect-aware coordinator; exception-only retry is unsafe when dispatch may have happened.
9. Distinguish tests that exist in the repository from tests actually executed and passed on the current HEAD.
10. Keep W12 finance/impact as architecture-only until source-level payment, ledger, custody and independent verification paths are traced.

## 12. Workstream impact

- **W01:** authority graph and grant issuer/registry/revocation constructor map.
- **W02:** ingress and runtime recovery/dispatch boundary map.
- **W03:** two journal roles, durable commit and volatile reservation distinction.
- **W04:** coordinator-injected gate and identity-bound result admission.
- **W05:** provider router/gateway/resilience construction graph remains open.
- **W06:** cryptographic attestation and evidence custody distinction.
- **W07:** signed simulation outputs do not establish calibrated reality.
- **W08:** durable monotonic anchor confirmed; outbox persistence still open.
- **W09:** signed grants, replay and revocation are strong local controls; distributed durability and trust-root lifecycle remain open.
- **W10:** specialist qualification remains a separate authority/evidence problem.
- **W11:** runtime ingress, adapters, recovery and deployment trust chain need complete mapping.
- **W12:** fund segregation and authorized adapters specified architecturally; production ledger/payment/impact source graph not established by this pass.

All W01–W12 remain **PARTIAL**. No stream is promoted to DECIDED/FROZEN. No ADR is accepted or closed by this document. No implementation, integration, tests, merge, deployment or release readiness is claimed.

## 13. Next bounded source pass

1. Enumerate all production constructors and factories for IdentityRegistry, AuthorizationAuthority, ActionGate, SessionAuthority, RuntimeEngine, both StateJournal classes, RecoveryController and OfflineRuntime.
2. Trace every ingress route to runtime adapters and deployment middleware/proxy exposure.
3. Enumerate every ProviderRouter/ProviderExecutionGateway/ResilientProviderExecutor caller and retry nesting.
4. Enumerate AgentCoordinator/AgentMesh/AgentFabric consumers and prove parent/child execution lineage.
5. Trace offline queue, monotonic anchor, cipher/key ID, remote inbox and acknowledgement persistence.
6. Enumerate financial/payment/ledger/escrow/impact implementation paths and adapters, not just architecture documents.
7. Trace release workflow, artifact provenance, runtime measurements, environment promotion and rollback.
8. Update W01–W12 source traceability only after each concrete call-site path is inspected.

