# NORYX7 — Execution Semantics, Agent Scheduling, Provider Effects and Distributed Fabric Reconciliation

**Review date:** 2026-11-24  
**Reviewed head:** `3b62dc69fe0c9db6d095be535cac28d24bc0ab67`  
**Scope:** architecture-only source reconciliation across W01–W12. No runtime, test, dependency, workflow or deployment files are changed.

## 1. Executive finding

NORYX7 now has multiple real bounded execution and trust primitives. The critical remaining architecture gap is semantic convergence: agents, providers, cross-front dispatch, offline execution, state commits and global placement do not yet share one canonical operation lifecycle and one consistent definition of success, failure, uncertainty, retryability and evidence admission.

The architecture must define a single operation envelope and lifecycle without prematurely collapsing the distinct adapters or surfaces.

## 2. Source findings on the reviewed head

### 2.1 HYPERSYNTH and agent scheduling — W02/W04/W05/W06

Inspected:
- `core/contracts.py`
- `core/hypersynth.py`
- `core/agent_core.py`
- `core/agent_mesh.py`
- `core/coordination.py`

Findings:
1. `Hypersynth.__init__` sets `bounded_steps = min(max_steps, max_agents)` and uses it to construct the default planner and ActionGate limits. Agent parallelism, number of plan steps and maximum authorized actions are therefore coupled in the default path, although they are distinct resource dimensions.
2. `AgentCoordinator.assign` iterates over `plan.steps[:max_agents]`. A plan longer than the agent bound is truncated at assignment rather than represented as a complete DAG with queued work, backpressure or an explicit incomplete-plan outcome.
3. `AgentCoordinator.execute` creates a fresh execution ID rather than accepting/binding the execution identity already carried by the task. The child task is built with this new ID. This risks splitting one logical orchestration into separate identity domains unless the caller contract explicitly reconciles them.
4. `AgentMesh.route` deterministically chooses the alphabetically first agent with the requested role. It does not inspect qualification, health, capacity, load, trust freshness, geography or independence.
5. `AgentCore.run` executes its plan steps sequentially under a per-agent lock. Its boolean `verify` callback is an adapter seam, not a source-anchored evidence proof.
6. Agent identity trust is checked before and after execution in the coordinator when an identity registry exists. This is a useful live trust boundary, but it does not itself prove the semantic correctness or independent provenance of the output.
7. `AgentCoordinator.verify_consensus` requires distinct agent IDs and equal outputs. Distinct IDs and output equality do not prove distinct models, datasets, providers, code paths, operators or failure domains.
8. `TaskSpec`, `ActionSpec` and `AgentResult` carry execution IDs, but there is no single common envelope here for principal, tenant, request, branch, plan, step, operation, attempt, provider, side-effect status and evidence lineage.

Required architecture:
- separate plan cardinality, agent concurrency, action budget, resource capacity and deadline budgets;
- preserve the entire DAG; assign only currently runnable nodes and explicitly report pending/blocked/failed/cancelled nodes;
- carry one caller-supplied canonical execution ID through HYPERSYNTH, JARVIS, child tasks, tool/provider calls, state commit and receipts;
- distinguish scheduler eligibility from role matching and identity trust;
- model qualification, live liveness, capacity, lease ownership, cancellation, retries and failure-domain independence;
- represent consensus as a typed evidence assessment, not equality of output strings.

### 2.2 Provider routing and external effects — W01/W02/W05/W06/W09/W11

Inspected:
- `core/provider_router.py`
- `core/provider_execution.py`
- `core/execution_fabric.py` (referenced by provider gateway)
- `ecosystem/runtime_dispatch.py`

Findings:
1. `ProviderRouter.execute` catches every provider exception, excludes that provider and retries another matching provider. An exception can occur before dispatch, during dispatch, after a remote effect committed, or while returning/decoding a response. These cases are not equivalent.
2. `ProviderExecutionGateway.execute` resolves a provider, builds a fresh ExecutionFabric and constructs `action_id=f"provider:{principal_id}:{provider.name}:{capability}"`. This ID is stable across repeated calls by the same principal/provider/capability and does not bind a unique logical request or attempt.
3. The provider gateway returns provider/capability/output, but its result envelope does not itself include a durable receipt, operation attempt, idempotency key, effect certainty, provider attestation or reconciliation status.
4. `runtime_dispatch.dispatch` catches handler exceptions and emits an accepted=false receipt; a successful handler produces accepted=true based on the return path and type evidence. A generic handler exception does not prove that no external side effect occurred.
5. The cross-front dispatch receipt and provider execution result are separate structures; neither is shown as the canonical receipt consumed by offline sync, state journal and global audit.

Required operation state machine:
`CREATED → AUTHORIZED → INTENT_DURABLE → DISPATCHING → EFFECT_CONFIRMED | EFFECT_REJECTED | EFFECT_INDETERMINATE → EVIDENCE_ADMITTED → STATE_COMMITTED → RECONCILED`.

Rules:
- retry only when dispatch is proven not to have occurred, or the target guarantees idempotency for the same immutable operation key;
- never change provider while an earlier attempt is indeterminate unless a reconciliation contract proves safe deduplication;
- a new attempt ID must not create a new logical operation ID;
- receipt must bind principal, target/provider identity, capability, policy version, request digest, operation ID, attempt ID, idempotency key, timestamps, effect status and evidence digest;
- compensation is a distinct authorized operation, never an assumption that rollback succeeded.

### 2.3 State journal and recovery — W01/W02/W03/W09/W11

Inspected:
- `core/state_journal.py`
- `core/recovery.py`
- `core/offline.py`

Findings:
- `StateJournal` uses SQLite WAL/FULL, transactional append, unique execution IDs, sequence validation and record digests. This is a meaningful durable local commit primitive.
- The record digest is stored in the same SQLite database; it is an integrity check, not an independently held signed checkpoint or externally witnessed append-only root.
- `RecoveryController` provides a monotonic in-process epoch and serializes `run_if_normal` against state transitions. Its lock and epoch are not a distributed recovery authority across processes, nodes or databases.
- `OfflineSyncQueue` is an encrypted bounded outbox held in a Python dictionary. Encryption and payload digest validation do not make the queue crash-durable.
- The offline snapshot binds principal, policy, artifact and state versions with capabilities and a digest; the injected authenticator and monotonic anchor remain external trust dependencies.
- The offline lifecycle and provider lifecycle need a common indeterminate-effect vocabulary. An exception or local queue acknowledgement cannot by itself prove a remote effect was absent or reconciled.

Required architecture:
- distinguish local durable commit, replicated durable commit and externally witnessed checkpoint;
- define recovery epochs across all durable stores and nodes;
- define outbox persistence, ordering, deduplication, retention, dead-letter, replay and conflict handling;
- retain uncertain external operations until reconciliation evidence is admitted;
- expose degraded context/state explicitly rather than silently treating unavailable persistence as empty state.

### 2.4 Memory and multimodal custody — W03/W06/W08/W09/W11

Inspected:
- `ecosystem/global_fabric.py`
- `core/multimodal.py`

Findings:
- `GlobalMemoryFabric.put` hashes payload and provenance bytes but stores a `MemoryRecord` containing digests and replica labels, not the payload bytes.
- `require_redundancy` counts replica identifiers; it does not query independent storage systems, verify reachability, durability, freshness or restore ability.
- `MediaRef` stores modality, content type, digest and locator. `MultimodalInput.build` computes a request digest over those fields. This is a reference envelope, not proof of encrypted custody, locator authorization, malware/content screening, consent, retention, deletion or derivative lineage.
- A locator is included in the digest but is not itself a trusted access capability.

Required architecture:
- canonical media artifact ID, immutable source digest, custody location and access capability must be separate;
- every transformation (OCR, transcription, frame extraction, crop, embedding, normalization, redaction) must create a child artifact with tool/model version and source offsets;
- memory records need tenant/principal/task/consent scope, classification, expiry, tombstone and replica-health attestations;
- replicas must be distinct failure domains and tested by read/restore, not counted by labels.

### 2.5 Egress, supply chain and global placement — W05/W08/W09/W10/W11

Inspected:
- `core/egress.py`
- `core/supply_chain.py`
- `core/resource_router.py`
- `ecosystem/global_scale.py`

Findings:
- `EgressPolicy` is an explicit in-memory allowlist of component/host/port/protocol tuples. It does not demonstrate DNS resolution pinning, redirect validation, proxy/socket enforcement or bypass resistance.
- `SupplyChainVerifier` verifies Ed25519 signatures from configured trusted keys and artifact SHA-256. Key lifecycle, signer role/rotation/revocation, SBOM, build provenance and deployment promotion remain separate requirements.
- `ResourceRouter` uses fixed complexity/privacy/latency thresholds to choose DEVICE/EDGE/CLOUD; it does not use live health, capacity, queue, residency, cost or energy.
- `GlobalControlPlane` and `CellRegistry` model region/cell health, latency, capacity and residency and select healthy capacity-compatible candidates. These are in-memory control-plane registries, not proof of live telemetry, distributed consensus, reservation/lease, durable queue, real worker orchestration or provider health.
- `GlobalTrafficRouter` selects a region and cell but does not itself reserve capacity or establish a durable placement lease. `ElasticComputeFabric` is an accounting layer; adapters perform actual scaling.

Required architecture:
- distinguish observed telemetry freshness from declared health;
- add capacity reservation/lease and release semantics with fencing tokens;
- define placement revalidation and failover under stale telemetry/network partition;
- hard-enforce privacy/residency/attestation constraints before scoring latency, cost, energy or carbon;
- bind software/model manifest and provider attestation to every placement decision.

## 3. Canonical operation envelope

All W01–W12 should consume a versioned envelope with at least:
`tenant_id, principal_id, issuer_id, session_id, device_or_workload_id, request_id, execution_id, branch_id, plan_id, step_id, operation_id, attempt_id, target_id, provider_id, capability, policy_digest, artifact_digest, data_classification, consent_ref, idempotency_key, deadline, placement_lease, effect_state, evidence_refs, audit_correlation_id`.

Fields may be null only when the operation class does not require them; absence must be typed and explicit, never inferred from a display name or agent role.

## 4. Cross-workstream dependencies

| Contract | Owners | Consumers |
|---|---|---|
| Principal/session/issuer/revocation | W01/W09 | W02/W04/W05/W08/W10/W12 |
| Canonical task/branch/plan/operation IDs | W02/W04 | W03/W05/W06/W08/W11 |
| DAG scheduler, leases and capacity | W02/W04/W05/W11 | W06/W07/W08/W10 |
| Effect certainty, idempotency and receipts | W02/W09/W11 | W04/W05/W08/W12 |
| Evidence and provenance envelope | W06 | W03/W04/W07/W08/W10/W12 |
| Media custody and transformation lineage | W03/W08/W09 | W06/W07/W10 |
| Placement policy and telemetry freshness | W05/W11 | W02/W04/W07/W08/W12 |
| Recovery epoch and durable outbox | W02/W03/W11 | all streams |
| Artifact/model attestation | W09/W11 | W02/W04/W05/W07/W08/W10 |
| Funds and outcome ledger | W12 | W06/W09/W10/W11 |

## 5. Existing ADR consolidation

No new ADR series is created.

| Existing ADR | Required reconciliation | Status |
|---|---|---|
| B79/B80/B85/B87 | One execution identity across front/branch/plan/step/attempt; no silent plan truncation; DAG scheduler and lease semantics | OPEN |
| B86/B104 | Provider/tool/offline effect certainty, idempotency, durable receipts and reconciliation | OPEN |
| B88/B90/B97 | Independent evidence lineage, consensus independence and semantic result admission | OPEN |
| B81/B103 | Memory custody, payload persistence, tenant isolation, tombstones and replica health | OPEN |
| B82/B102 | Principal, issuer, session and device/workload authority continuity | OPEN |
| B71/B96/B98 | DNS/socket egress enforcement, provider identity and safe research acquisition | OPEN |
| B72/B77/B89 | Trusted artifact/model signing, external checkpoint and evidence-backed freeze | OPEN |
| B91 | Campaign execution evidence and independent holdout custody | OPEN |
| B94 | Multimodal custody, transformation lineage, consent and retention | OPEN |
| B95 | Global placement telemetry, capacity lease, production adapters and failure domains | OPEN |
| B76/B99 | Specialist qualification and scheduling eligibility | OPEN |
| B83/B84/B101 | Financial custody, governance and independently verified outcomes | OPEN |

## 6. W01–W12 impact

- W01 identity must bind every operation and attempt to a canonical principal/session.
- W02 runtime must own a single execution lifecycle and reconcile local, offline and provider effects.
- W03 memory must distinguish metadata index from durable payload custody.
- W04 agent assignment must preserve complete plans and use qualified, live, capacity-aware scheduling.
- W05 placement must combine hard residency/trust constraints with fresh telemetry and leases.
- W06 verification must distinguish structural checks, semantic evidence, formal proof and empirical validation.
- W07 MIRROR WORLD must bind experiment/model artifacts to the same evidence and operation envelope.
- W08 surfaces must use consistent request, capability, artifact and outbox contracts.
- W09 egress, signing, authorization and effect reconciliation must be enforced at actual boundaries.
- W10 specialist role must be qualified and scope-limited, not inferred from role labels.
- W11 operations must expose freshness, saturation, uncertain effects, recovery epoch and durable audit.
- W12 funds and environmental outcomes must use operation receipts and independent outcome evidence.

All W01–W12 remain **PARTIAL**. This document is an architecture reconciliation, not implementation, integration proof, CI pass, production readiness or architecture freeze.

## 7. Next architecture-only work

1. Build a call-site and dataflow map for every operation envelope field across HYPERSYNTH, JARVIS, provider execution, runtime dispatch, offline and state journal.
2. Resolve the execution-ID split between caller task and coordinator-generated execution.
3. Specify complete DAG scheduling without truncation and with explicit bounded admission.
4. Define provider attempt/idempotency/effect certainty and canonical receipts.
5. Map storage durability domains and recovery epoch propagation.
6. Specify media custody and global replica verification.
7. Reconcile placement lease and telemetry freshness with W11 reliability and W12 energy/cost accounting.
8. Only after source traceability and contract review across W01–W12, decide architecture closure; integration and comprehensive verification remain subsequent phases.
