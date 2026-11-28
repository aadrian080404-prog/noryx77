# NORYX7 — Memory, Model Routing, Evidence and Distributed Execution Reconciliation

**Audit date:** 2026-11-27  
**Audited source-tree commit:** `491738a688771effde756a6779a455ef514b8587`  
**Scope:** cross-stream source reconciliation for W01–W12, with emphasis on memory custody, model/provider routing, evidence production, offline synchronization and global placement.  
**Disposition:** source-grounded architecture findings and proposed closure contracts only. No runtime implementation, tests, workflows, deployment configuration or frozen baseline changed.

## 1. Executive finding

The inspected repository has substantial local building blocks: bounded working memory, an L0–L5 hierarchy, encrypted record adapters, AES-GCM/HKDF primitives, offline admission and encrypted outbox, capability-aware model routing, provider execution gates, evaluation-case generation, synthetic cyber-range workflows, event-fusion/forecasting primitives, supply-chain signatures and global region/cell registries.

The main remaining issue is not a lack of primitives. It is the boundary between a local primitive and an end-to-end service:

- encrypted record APIs still retain ciphertext in an in-process dictionary unless a real persistence adapter is supplied;
- the global memory fabric stores digests, version and replica labels, not replicated payloads or durable consensus;
- model selection is capability/cost/latency ranking, while model fan-out executes sequentially and a verifier callback's score is not independently calibrated;
- provider failover can interpret any handler exception as a reason to call another provider, although an exception may follow a completed external side effect;
- offline acknowledgement removes the local outbox item based on caller-supplied execution ID and optional version equality, without a typed remote commit receipt in the inspected API;
- evaluation campaigns generate reproducible cases and holdout assignments but do not execute the cases or independently attest result evidence;
- CyberRange reports symbolic synthetic actions as verified; it is not a general systems reverse-engineering engine or evidence of real target behavior;
- FINCH produces deterministic heuristic anomaly and mean-severity forecasts, not calibrated event probabilities;
- global capacity selection is not a fenced, durable reservation or deployment admission protocol.

The architectural task is to compose, persist, authenticate and independently verify these boundaries before claiming distributed operation or production assurance.

## 2. Exact source anchors

All paths below were inspected at source snapshot `491738a688771effde756a6779a455ef514b8587`; blob SHAs identify the exact files:

| Source path | Blob SHA | Bounded observation |
|---|---|---|
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` | Bounded process-local MemoryStore with execution filtering and deep-copy isolation |
| `core/memory_hierarchy.py` | `d908fcb7252e97072501b94dada23ae571807850` | In-process L0–L5 key/value hierarchy and explicit level promotion |
| `core/secure_memory.py` | `27727ce69802f3ad4f082bf4b9bc4ef013fa7812` | JSON serialization adapter over EncryptedRecordStore |
| `core/secure_storage.py` | `0fd726f2bad1ff6e133b46c04039ae2c943d350f` | AES-GCM ciphertext map, AAD binds namespace and record ID; backing dictionary is local |
| `core/crypto.py` | `ce0f534fb6f786838325dc22469c2364aee4ee9b` | AES-256-GCM, 96-bit nonce, HKDF-SHA256, injected KeyProvider; InMemoryKeyProvider explicitly test-only |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` | Global memory metadata index with digest/version/replica labels; external storage/transport remain adapters |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Authenticated snapshot callback, offline policy/verifier, encrypted in-memory outbox and caller-triggered sync acknowledgement |
| `noryx7_runtime/model_fabric.py` | `abb8bd9bb3217fff967e898afbdc491eb5082f45` | Capability/cost/latency ranking, sequential adapter execution, optional verifier/synthesizer, result digest/MAC |
| `core/llm/model_fabric_bridge.py` | `544dd80facf249278adbb797b276f82935564305` | Text-only single-model bridge; no tools exposed to the model |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` | Ordered capability routing and exception-triggered provider failover |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` | Per-call authorization through ExecutionFabric before provider handler |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | Bounded failover attempts; exception triggers alternate provider |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` | Deterministic case and holdout manifests; accepts externally produced pass/score/evidence |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` | Symbolic actions against synthetic sandbox targets only |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Keyword/severity relevance, severity-deviation anomalies, mean-severity forecast |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Trusted Ed25519 manifest signature and artifact byte digest verification |
| `core/universal_intelligence.py` | `986dd5976b6451a5a75950535c13f4355f57fb0f` | Domain keyword routing and evidence-bearing assessment contracts |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` | In-process region/cell health, capacity and selection primitives |

The inspection is bounded to these source definitions. It does not claim that external database, KMS, provider, monitoring, fleet or storage adapters are absent from every deployment.

## 3. Findings by cross-stream concern

### 3.1 Memory tiers are currently different local abstractions, not one coherent tiered service

- `MemoryStore` is bounded, process-local, thread-safe and isolates reads/writes by deep copy. It supports kind labels and optional execution scoping.
- `MemoryHierarchy` is a separate minimal in-process key/value map with L0–L5 levels and promotion. It does not share the MemoryItem schema, execution scope, provenance or encrypted persistence interface.
- `EncryptedMemoryStore` serializes MemoryItem with schema version 1 and delegates to EncryptedRecordStore.
- `EncryptedRecordStore` retains encrypted envelopes in a local dictionary. Its AAD binds namespace and record ID; it returns ciphertext snapshots for an external backend, but the inspected class itself does not persist them across process restart.
- `GlobalMemoryFabric` retains metadata: record ID, level, version, payload digest, replica IDs and provenance digest. Its own documentation states encryption, durable storage and transport remain adapters. The replica tuple is declared metadata, not proof that replicas received or durably committed bytes.

Consequences:
1. L0–L5 labels in MemoryHierarchy are not automatically equivalent to the global fabric's L0_DEVICE…L5_ARCHIVAL enum.
2. Promotion currently changes a local level field; it does not prove durable tier migration, replication, retention or deletion propagation.
3. A ciphertext snapshot is a backend handoff, not a completed backup/restore proof.
4. Execution-scoped access in MemoryStore/EncryptedMemoryStore does not by itself define tenant isolation, user ownership, legal retention, deletion propagation or cross-device conflict policy.

**Closure requirement:** define one canonical MemoryRecord envelope and versioned adapters for working memory, encrypted local store, durable regional backend and global index. Each tier transition needs source/destination receipt, payload digest, encryption/key version, policy/tenant scope, replication quorum, retention/deletion semantics and recoverability evidence. Replica metadata must be populated only from authenticated acknowledgements.

### 3.2 Cryptographic primitives are stronger than the currently demonstrated key operations

The crypto module uses AES-256-GCM with a 96-bit random nonce, 128-bit authentication tag and HKDF-SHA256 domain-separated subkeys. AAD includes the key ID and caller-provided associated data. The key boundary is injectable, and InMemoryKeyProvider is explicitly test-only.

The inspected crypto/store path does not itself provide a production KMS/HSM implementation, key creation/rotation/revocation/destruction policy, key backup/recovery, access audit, tenant-level key hierarchy or migration of ciphertext between key versions. A caller can inject an appropriate KeyProvider, but production-grade key custody must be proven at the composition root and operational environment.

**Closure requirement:** key lifecycle contract with issuer, key purpose, tenant/domain separation, version, activation/retirement, rotation overlap, revocation, recovery, destruction evidence and audited access. Rotation must specify re-encryption or envelope-key migration without silently losing old records.

### 3.3 ModelFabric selection and provenance do not equal independent model consensus

ModelFabric:
- filters models by required capabilities, optional cost and latency bounds;
- ranks by preferred capability overlap, expected latency, cost and name;
- runs selected adapters sequentially in the inspected `execute` loop;
- can require a minimum number of candidate outputs;
- optionally calls a verifier callback and a synthesizer callback;
- binds request/result metadata with deterministic digests and optionally HMACs the result envelope to a runtime key.

The result digest/MAC is integrity/provenance for the fabric's envelope; it is not a truth certificate for model content. The confidence value is the supplied verifier's bounded numeric score, or zero without a verifier. No calibration dataset, evaluator independence, source entailment or confidence calibration is established by this module. A multi-model request is fan-out by candidate count but not parallel execution in this implementation.

The LLM bridge intentionally requests one text model and no tools, preserving tool execution outside the model. This is a useful separation, but it is not the complete agent ensemble or independent verification layer.

**Closure requirement:** distinguish candidate diversity, execution concurrency, evaluator independence, synthesis and semantic admission. Bind each candidate to model/provider/version, prompt/request digest, raw output digest, runtime/execution, cost/latency, failure and evaluator profile. Confidence must be calibrated for a declared task/domain or labelled uncalibrated. No model output is promoted to an action or trusted memory solely because its envelope MAC verifies.

### 3.4 Provider failover has an ambiguous-effect boundary

- ProviderRouter selects the first registered provider with the requested capability and retries another provider after any handler exception.
- ProviderExecutionGateway authorizes the principal/capability/target through ExecutionFabric before calling the selected handler.
- ResilientProviderExecutor records bounded attempts and also excludes a provider after an exception, then attempts another provider. Policy denial is terminal.

These abstractions do not share a canonical operation ID, idempotency key, target-side lookup or EffectReceipt. The exception path does not distinguish a pre-effect failure from a timeout/exception after the remote system already applied the request. Retrying against another provider may therefore duplicate an external effect if the operation is non-idempotent. This is a recovery-design risk, not proof that a specific provider currently duplicates transactions.

**Closure requirement:** classify provider operations as read-only, idempotent-write, deduplicated-write or non-idempotent. Require stable operation/attempt IDs and a target-supported idempotency key for writes. On ambiguous outcomes enter EFFECT_UNKNOWN and reconcile against target state before failover. Failover must be a policy decision, not an automatic consequence of arbitrary exceptions.

### 3.5 Offline outbox acknowledgement is not yet a typed remote commit proof

OfflineRuntime verifies snapshot authenticity through an injected callback, checks age/version/capability/principal, invokes an offline policy, uses a recovery epoch guard, verifies the result and calls a local commit callback. It then marks the operation sync-pending and returns an encrypted SyncEnvelope.

On reconnection it requires caller booleans for authenticated/channel-verified. `acknowledge_synced` looks up a matching execution in the local queue, rejects a conflict or optional remote state version mismatch, and removes the queue item. The inspected method does not receive a signed remote commit receipt binding the exact execution, ciphertext digest, target transaction, remote state version, policy epoch and durable-commit identity. The queue and sequence are in-process state.

**Closure requirement:** introduce a RemoteCommitReceipt signed by the remote authority and bound to execution ID, operation ID, payload/ciphertext digest, sequence, principal, base/new state version, target transaction, receiver identity and commit timestamp. Persist outbox/inbox and acknowledgement atomically; replay and duplicate delivery must be idempotent. Queue deletion occurs only after receipt validation and durable local acknowledgement record.

### 3.6 Evaluation, cyber simulation and event forecasting have distinct evidence ceilings

- EvaluationCampaign creates deterministic generated-case and holdout manifests. It does not execute scenarios; `record` accepts externally produced pass/score/evidence and `approve` aggregates matrix dimensions. Holdout separation and evaluator evidence must be enforced by a separate runner.
- CyberRange uses synthetic sandbox targets and symbolic phase/action records. Its report's `verified=True` is a local report field; no real target exploitation or general system reconstruction is performed.
- FINCH builds a bounded graph and ranks relevance/anomalies using keyword and severity formulas. Its forecast likelihood is the mean of supplied severities by subject; no statistical calibration or predictive validation is performed in the module.
- UniversalIntelligenceFabric routes domains by keyword scores and defines evidence-bearing assessments. It does not verify specialist credentials or independently establish evidence truth.
- SupplyChainVerifier checks a manifest signature against explicitly trusted Ed25519 public keys and compares artifact bytes to the signed digest. This proves integrity relative to the trusted key list, not a complete reproducible build, source provenance, dependency/SBOM completeness, build isolation, release approval or rollback.

**Closure requirement:** create separate evidence profiles for (a) generated test case, (b) executed test run, (c) independent evaluation, (d) synthetic simulation, (e) observed real-world experiment and (f) production release. FINCH outputs must be labelled heuristic until calibrated against representative, temporally separated data with confidence intervals, drift monitoring and false-positive/negative measurement. CyberRange must never be presented as proof of live-system behavior. Supply-chain closure needs build provenance, source-to-artifact trace, dependency manifest, builder identity, policy, release approval and rollback evidence.

### 3.7 Global scale registry is not a resource reservation or deployment controller

GlobalControlPlane and CellRegistry maintain in-process registries and select healthy regions/cells with capacity-fit filters. The global fabric similarly indexes memory and identity authorization metadata. These primitives are useful control-plane models but do not by themselves reserve capacity atomically across processes, issue fenced expiring leases, prove node identity/attestation, decrement shared capacity under concurrency, replicate control-plane state or prove restore/deployment completion.

**Closure requirement:** introduce PlacementLease with issuer, resource vector, region/cell, workload, tenant/residency, policy epoch, TTL, fencing token, node attestation, reservation version, renewal/release and crash recovery. Couple it to a durable scheduler ledger and deployment/health evidence. A region selection is not a reservation; a reservation is not proof of a deployed healthy workload.

## 4. Cross-workstream closure map

| Workstream | Current source boundary | Required architecture closure |
|---|---|---|
| W01 Identity/trust/authorization | injected key and policy callbacks; local identity indexes | authenticated issuer profiles, principal/device/tenant binding, key lifecycle and revocation |
| W02 Runtime/orchestration | local execution and provider dispatch abstractions | one operation coordinator, ambiguous-effect handling, typed receipt promotion |
| W03 Memory/state/recovery | local stores/journals and optional persistence adapters | canonical memory contract, durable commit/replay, retention and deletion propagation |
| W04 Agent fabric | agent/task/skill/result primitives | qualified delegation, model/agent provenance and independent result admission |
| W05 Routing/providers/resources | capability ranking and provider failover | idempotency-aware routing, leases, cost budgets and target reconciliation |
| W06 NEXUS/FRL/evidence | generated manifests, structural evidence and assessments | source custody, claim/proof graph, independent evaluator and calibrated confidence |
| W07 MIRROR WORLD | synthetic cyber range and simulation contracts | fidelity manifests, experiment controls, measured reality bridge and no synthetic-to-real proof promotion |
| W08 Surfaces/devices/browser/offline | encrypted outbox and local surface bridges | durable sync protocol, device-bound receipts and authenticated remote commit |
| W09 Security/crypto/audit/release | strong primitives and trusted-key checks | production KMS/HSM, signed audit, build provenance, release and rollback chain |
| W10 Specialist/domain intelligence | keyword routing and evidence-bearing proposals | issuer-verified qualification, jurisdiction, domain-specific validation and escalation |
| W11 Global distribution/operations | region/cell selection and metadata registries | fenced leases, durable replication, SLO/DR, node attestation and measured deployment |
| W12 Economy/governance/impact | generic execution/evidence building blocks | separate payment/ledger/settlement/refund states and independently measured impact evidence |

## 5. Proposed shared contracts (not accepted ADRs)

### Memory and custody
- `MemoryRecordEnvelope`: record_id, schema_id/version, owner/tenant, classification, execution/operation lineage, content digest, encrypted object reference, key ID/version, provenance, retention/deletion policy, replication policy and lifecycle.
- `TierTransferReceipt`: source/destination tier, record digest, source/destination storage IDs, encryption/key version, replica acknowledgements, policy decision and verified completion.
- `MemoryRecoveryReceipt`: backup manifest, restore point, integrity result, recovered object count/digests and recovery environment.

### Model and provider execution
- `ModelCandidateReceipt`: request digest, provider/model/version, raw output digest, latency/cost, failure state, runtime/execution, tools declaration and adapter identity.
- `ModelEvaluationReceipt`: evaluator identity/profile, task/domain, rubric version, source references, calibration version, score and uncertainty.
- `ProviderAttemptReceipt`: operation/attempt IDs, principal, provider, capability, target, idempotency key, request digest, dispatch time and outcome certainty.
- `ProviderEffectReceipt`: target-side transaction/effect ID, observed state, exact request/effect digest, observer identity and signature.

### Offline and distributed operation
- `RemoteCommitReceipt`: execution/operation IDs, sequence, payload digest, principal, target transaction, base/new state version, receiver identity, durable commit marker and signature.
- `PlacementLease`: workload, tenant, resource vector, region/cell, policy epoch, expiry, fencing token, node attestation and durable reservation ID.

### Evidence and reality bridge
- `EvaluationRunReceipt`: immutable case/holdout manifest, runner build, evaluator identity, raw output, test environment, result and evidence digest.
- `SimulationEvidenceProfile`: model/kernel/version, world manifest, assumptions, calibration domain, uncertainty and explicit synthetic-only scope.
- `RealityObservationReceipt`: source instrument/observer, timestamp/clock, target, measurement method, raw evidence digest, custody and independent review.
- `ReleaseProvenanceReceipt`: source revision, dependency/SBOM digest, builder identity, reproducible build evidence, artifact digest, signer, policy approval, canary and rollback anchor.

These are design proposals; existing types are not silently renamed or replaced.

## 6. New gap register entries

- `GAP-MEMORY-TIER-TRANSFER-AND-DURABLE-CUSTODY`
- `GAP-KEY-LIFECYCLE-AND-PRODUCTION-KMS-COMPOSITION`
- `GAP-MODEL-ENSEMBLE-INDEPENDENCE-AND-CALIBRATION`
- `GAP-PROVIDER-FAILOVER-UNKNOWN-EFFECT-AND-IDEMPOTENCY`
- `GAP-OFFLINE-REMOTE-COMMIT-RECEIPT-AND-DURABLE-OUTBOX`
- `GAP-EVALUATION-RUNNER-HOLDOUT-AND-INDEPENDENT-EVIDENCE`
- `GAP-SIMULATION-REALITY-EVIDENCE-AND-FINCH-CALIBRATION`
- `GAP-GLOBAL-PLACEMENT-LEASE-AND-DEPLOYMENT-ATTESTATION`
- `GAP-SUPPLY-CHAIN-BUILD-PROVENANCE-AND-ROLLBACK`

These gaps describe architecture closure requirements in the inspected source paths, not verified vulnerabilities or universal absence of external services.

## 7. Disposition

This audit does not authorize integration, tests or architecture freeze. The next architecture-only pass must map every production composition root and external adapter to these contracts, identify accountable owners, and resolve the outstanding decisions. Only after all W01–W12 are architecturally closed should implementation integration begin, followed by end-to-end verification and validation.

**W01–W12 remain PARTIAL.**
