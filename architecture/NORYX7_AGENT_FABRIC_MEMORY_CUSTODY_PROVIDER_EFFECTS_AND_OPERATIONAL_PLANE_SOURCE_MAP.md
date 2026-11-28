# NORYX7 — Agent Fabric, Memory Custody, Provider Effects and Operational Plane Source Map

**Status:** architecture-only source reconciliation; findings are bounded to the exact source snapshot below  
**Repository:** `aadrian080404-prog/noryx77`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Inspected HEAD:** `4889dd52aa4b7aec737ed4f910f6f77e6e7fa978`  
**Date:** 2026-11-25  
**Scope:** W01–W12 cross-stream continuation; source constructors, registries, dispatch, memory custody, provider retry, device/browser surfaces, forecasting and release trust.

> This document records source facts and architecture requirements. It does not certify runtime wiring, production readiness, test coverage, or workstream closure. No runtime or test file is changed by this document.

## 1. Evidence discipline

- A source path and blob SHA identify the exact file version inspected at the stated HEAD.
- A class or adapter proves only the behavior visible in that source; it does not prove all callers use it.
- In-memory registries are not durable distributed registries.
- A successful handler return is not proof that an external-world effect occurred exactly once.
- A digest or signature proves only the bytes and claims within its defined scope.
- Forecast likelihoods are not calibrated probabilities unless evaluated against representative, temporally valid holdouts with calibration evidence.
- W01–W12 remain **PARTIAL**. This pass does not close any workstream.

## 2. Source snapshot and exact anchors

| Source | Blob SHA | Bounded observation |
|---|---|---|
| `core/agent_fabric.py` | `3704dd7bf66815274cc319c9583c45ae575f3d36` | Bounded native-agent registry; validates identity, skills and principal authorization; candidate iteration is sorted by agent ID and returns the first authorized non-failed agent. |
| `core/agent_runtime.py` | `c6e0b0edd40fdcfc2264e8dc19ba5ae43b0187da` | Per-runtime lifecycle snapshot and heartbeat; online state derives from local router agents and identity trust. |
| `core/agents.py` | `23286d646aa55cbef669e1ddf7228df64bbb01ca` | Agent interface plus deterministic implementation with task/output verification; abstract base method remains unimplemented. |
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` | Bounded, lock-protected in-process MemoryStore with validation and defensive copies. |
| `core/memory_hierarchy.py` | `d908fcb7252e97072501b94dada23ae571807850` | Bounded L0–L5 key/value hierarchy and explicit promotion; dictionary-backed in this implementation. |
| `core/secure_memory.py` | `27727ce69802f3ad4f082bf4b9bc4ef013fa7812` | EncryptedMemoryStore serializes MemoryItem and delegates encrypted records to EncryptedRecordStore; constructor receives cipher, namespace and capacity. |
| `jarvis/memory/store.py` | `85123bbfe425ed21e7cd7d2dd2a55fdbb532a05d` | Separate small JARVIS MemoryStore with its own in-process storage. |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` | Capability-based provider registry and deterministic resolution; no performance or capacity score is visible in this source. |
| `core/http_provider.py` | `d40c9e4ffb9c830dc3307fe8a9b4c7bcf34c307f` | Bounded JSON-over-HTTP adapter; rejects redirects by handler, supports TLS config, limits response bytes, and leaves retry/failover to another layer. |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` | ProviderExecutionGateway creates an ExecutionFabric per call and authorizes immediately before dispatch. |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | Separate bounded failover executor; retries another provider after exceptions, with attempt records, but no external-effect reconciliation or idempotency contract visible here. |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Ed25519 signature validation against configured trusted public keys and artifact-byte digest verification. |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Bounded event graph, relevance/anomaly heuristics and subject forecast whose likelihood is mean severity. |
| `core/device_fabric.py` | `3b0ead031e03040d25bb7df3a716aaa50fa8591c` | In-process device registry with capability and online flag. |
| `ecosystem/browser_isolation.py` | `73f69b55f7bb6335d6e9294c7d48ebac1868991a` | Static repository source scanner and gate; source scan alone is not a browser process sandbox or network egress boundary. |

## 3. Cross-stream findings

### 3.1 Agent identity, registry, runtime and qualification are distinct layers

**Observed**
- `AgentFabric` validates the binding type, agent/identity ID match, identity well-formedness, declared skills, skill registration and trust at registration.
- Dispatch rejects principal-context spoofing, binds the principal into request context, snapshots bindings in sorted ID order, rechecks identity trust, invokes a principal authorizer, and dispatches to the first candidate that passes.
- `AgentRuntime` separately derives ONLINE/UNTRUSTED state from a router and identity registry; heartbeat refreshes the local snapshot.
- The operational fabric, router-backed runtime status, and the earlier `AgentMesh` role-selection path are therefore separate abstractions in the inspected source set.

**Not established**
- A canonical registry shared by every agent constructor, runtime, mesh and coordinator.
- A measured competence profile, calibration history, task-specific success rate, live load, resource reservation, fault-domain independence or evaluator independence.
- A durable cross-node agent identity/revocation and heartbeat protocol.
- Whether every production ingress reaches the same fabric and lifecycle authority.

**Architecture requirement**
Define one AgentDescriptor and one AgentBinding lifecycle with immutable identity, role taxonomy, skill evidence, qualification scope, model/tool permissions, resource envelope, health lease, trust epoch, execution lineage, evaluator independence and revocation state. Selection should return a reasoned ranked set plus an auditable decision, not silently select by lexical order. Eligibility must be fail-closed; ranking must never override authorization.

### 3.2 Memory hierarchy, secure memory and JARVIS memory need one custody contract

**Observed**
- `core.memory.MemoryStore` and `MemoryHierarchy` are bounded in-process structures.
- `EncryptedMemoryStore` is an adapter over `EncryptedRecordStore`, with a caller-supplied cipher and key ID on write.
- `jarvis.memory.store.MemoryStore` is another separate store.
- Encryption at an adapter boundary does not by itself establish durable storage, replication, recovery, retention enforcement, deletion propagation, or key availability after restart.

**Architecture requirement**
Specify canonical MemoryRecord, namespace/tenant/execution scope, provenance, sensitivity, retention and deletion state, version, encryption envelope, key reference, integrity digest, replication policy, snapshot watermark and recovery proof. Define adapters for hot working memory, suspended memory, durable journal and distributed replicas. Promotion L0–L5 must preserve provenance and authorization; it must not imply truth or permanent retention. Hydration must be scoped and auditable. Key rotation and cryptographic erasure must be coordinated with replicas, snapshots and backups.

### 3.3 Provider request, dispatch, remote effect and reconciliation need a single state machine

**Observed**
- `HttpJsonProvider` is a transport adapter with response limits and redirect rejection; it has no retry policy in this class.
- `ProviderExecutionGateway` and `ResilientProviderExecutor` are distinct execution paths.
- The resilience path can fail over after a provider exception. The inspected code does not establish whether a remote provider completed an effect before the exception was raised.
- Attempt records describe provider attempts, not necessarily the state of an external system.

**Architecture requirement**
Adopt one EffectExecution state machine with at least: PROPOSED, AUTHORIZED, DISPATCH_INTENT_DURABLE, DISPATCHED, ACKNOWLEDGED, EFFECT_OBSERVED, EFFECT_VERIFIED, COMMITTED, REJECTED, FAILED_NO_EFFECT, and OUTCOME_UNKNOWN. A timeout after dispatch must enter OUTCOME_UNKNOWN until reconciliation; it must not be treated as proof of failure. Retry only with a provider-supported idempotency key or after a domain-specific read/reconciliation step. Bind receipts to canonical request bytes, provider identity/version, idempotency scope, remote correlation ID, response bytes/digest, observed state and independent verifier.

### 3.4 Release trust has a useful cryptographic primitive, not yet a full release chain

**Observed**
- `SupplyChainVerifier` checks signer membership in an explicitly configured trusted-key set, validates Ed25519 over a manifest digest, and can compare the actual artifact bytes with the manifest digest.

**Not established by this class**
- Key issuance/rotation/revocation, threshold approvals, builder identity, reproducible builds, dependency/SBOM attestations, provenance of the build environment, promotion between environments, deployment observation, rollback verification or emergency revocation propagation.

**Architecture requirement**
Model the release as a linked attestation graph: source revision → dependency lock/SBOM → builder identity and environment → build invocation → artifact digest → signer/key epoch → policy approvals → staged promotion → deployment receipt → runtime measurement → rollback or revocation event. Every link must bind immutable identifiers and timestamps; no single manifest signature should be described as end-to-end release assurance.

### 3.5 FINCH scores must not be presented as calibrated forecasts

**Observed**
- Relevance combines severity and keyword match.
- Anomaly score combines severity and deviation from the batch mean.
- Forecast likelihood is the arithmetic mean of severity values grouped by subject, and evidence lists up to four observation IDs.

**Architecture requirement**
Represent forecasts as typed hypotheses with target event, horizon, base rate, cohort, model/version, input evidence IDs, missingness, uncertainty interval, assumptions and expiry. Calibrate using time-separated, leakage-resistant holdouts; report Brier score/log loss, calibration curves, coverage and drift by domain. Until those artifacts exist, label current values as heuristic scores, not probabilities or risk percentages.

### 3.6 Device and browser surfaces are not equivalent to trusted execution boundaries

**Observed**
- `DeviceFabric` tracks local device capabilities and online state.
- `browser_isolation` performs static source scanning.
- These primitives do not, by themselves, attest secure boot, isolate renderer processes, enforce network egress, bind a remote device to a hardware-backed identity, or prove that a browser action had the claimed effect.

**Architecture requirement**
Define a SurfaceTrust contract for browser, device, edge node and cloud worker: measured software identity, session binding, capability lease, egress policy, process isolation, data classification, action receipt, telemetry provenance, revocation and recovery. Distinguish policy intent from enforced boundary and measured runtime state.

## 4. W01–W12 impact matrix

| Workstream | New source-level clarification | Remaining closure evidence |
|---|---|---|
| W01 Identity | AgentFabric performs identity and principal checks, but multiple registries and runtime views remain. | Canonical authority, lifecycle, revocation and cross-node trust epochs. |
| W02 Runtime | Provider execution has multiple gateways and state transitions. | One runtime/effect lifecycle and ingress-to-runtime call graph. |
| W03 Memory | Hot, hierarchical, encrypted and JARVIS stores coexist. | Canonical memory custody, durable adapter, replication, recovery and deletion proof. |
| W04 Agent Fabric | Native fabric is principal-authorized but lexically first-match. | Unified registry, qualification, DAG lineage, concurrency, evaluator independence and semantic aggregation. |
| W05 Routing | Provider/device registries expose capability matching. | Capacity leases, measured health, cost/latency policy, placement constraints and reservations. |
| W06 NEXUS / Evidence | FINCH forecast evidence is observation IDs, not a complete claim/evidence graph. | Claim/evidence schema, source spans, authority, independence, contradiction and correction lifecycle. |
| W07 MIRROR WORLD | Existing event and cyber primitives are bounded and domain-specific. | Model adapters, real-world calibration, uncertainty, experiment ledger and sim-to-real validation. |
| W08 Interfaces | Browser/device primitives have partial local controls. | Surface trust, egress enforcement, consent, effect receipts and cross-surface identity. |
| W09 Security | Artifact signature verification is present. | Key lifecycle, hardware/remote attestation, policy-bound egress and complete release provenance. |
| W10 Specialist Domains | Skill labels exist, but measured qualifications are not established by these registries. | Domain credential, benchmark, recency, conflict-of-interest and evaluator qualification. |
| W11 Operations | FINCH and release primitives produce bounded artifacts. | Independent evaluation, SLO/error budgets, calibrated forecasting, incident/recovery and deployment evidence. |
| W12 Ecosystem | This source pass does not establish production finance or impact accounting. | Double-entry ledger, payment/escrow controls, dispute/chargeback, governance, consent and independently verified impact. |

## 5. Shared canonical contracts to design before integration

1. **AgentDescriptor / AgentBinding:** immutable agent identity, qualified skills, trust epoch, resource envelope, health lease, delegation scope and evaluator independence.
2. **ExecutionEnvelope:** principal, session, policy version, capability grants, request digest, parent/child execution IDs, deadline, budget and cancellation semantics.
3. **EffectRecord:** durable intent, dispatch attempt, remote correlation, idempotency key, observed effect, independent verification and terminal reconciliation.
4. **EvidenceRecord / ClaimRecord:** source artifact identity, exact span, collection time, authority/scope, transformations, support/contradiction edges, independence group, uncertainty, reviewer, correction and expiry.
5. **MemoryRecord:** namespace, provenance, retention, sensitivity, key epoch, replica/snapshot state, integrity and recovery watermark.
6. **ForecastRecord / SimulationRun:** model/version, domain, assumptions, scenario inputs, calibration cohort, uncertainty, holdout evidence and explicit simulated-vs-observed type.
7. **ReleaseAttestation:** source, dependency, builder, artifact, signer, approvals, promotion, deployment, runtime observation and rollback lineage.
8. **SurfaceTrustLease:** browser/device/edge/cloud identity, measurement, capability scope, egress policy, expiry, revocation and receipt.

These are proposed shared contracts, not existing implemented classes.

## 6. Dependency and sequencing implications

- W01 authority and W02 execution identity precede W04 delegation, W05 resource placement and W08 surface execution.
- W03 memory custody is a dependency of W06 evidence retention, W07 experiment reproducibility and W11 audit.
- W06 evidence semantics are a dependency of W07 model calibration, W10 qualification and W11 independent evaluation.
- W09 key/release trust is a dependency of remote agent, provider, browser and device trust.
- W12 financial and impact claims must consume the same evidence and audit model; payments must not be used as a substitute for verified impact.
- Integration must wait until these shared contracts and ownership decisions are resolved. This document does not authorize implementation or test changes.

## 7. Architecture decisions to reconcile (do not duplicate ADRs)

Map this pass into existing open decisions rather than creating duplicate ADRs:
- Agent registry, role/skill ontology, qualification and independent evaluation → existing agent-fabric/delegation and specialist-domain decisions.
- Canonical effect lifecycle, provider failover, idempotency and uncertain outcomes → existing runtime/provider/effect decisions.
- Memory adapter, key lifecycle, durable snapshots and distributed recovery → existing memory/state/recovery/security decisions.
- Evidence graph, source authority, forecast calibration and simulation provenance → existing NEXUS/MIRROR WORLD/evaluation decisions.
- Surface trust, egress and artifact/release chain → existing security/browser/device/supply-chain decisions.
- Ledger, escrow, governance and impact evidence → existing W12 ecosystem decisions.

The exact ADR identifiers and statuses must be taken from the current Architecture Decisions Backlog before editing that register; no new ID is inferred here.

## 8. Closure gates

A workstream may move from PARTIAL only when all applicable conditions are evidenced:
- Canonical contract and owner are approved.
- All constructors, registries, adapters, callers and ingress paths are mapped.
- Duplicate or parallel authorities are either unified or explicitly isolated with conversion boundaries.
- Failure, timeout, cancellation, retry, replay, recovery and revocation states are specified.
- Security and privacy invariants are stated and threat-modeled.
- Operational metrics, audit events and retention are defined.
- Integration and independent test plans are mapped to the contract.
- Evidence is tied to an immutable source revision and exact verification scope.

**Current disposition:** W01–W12 remain PARTIAL. Architecture discovery continues; no integration, general test campaign, merge or deployment is authorized by this pass.
