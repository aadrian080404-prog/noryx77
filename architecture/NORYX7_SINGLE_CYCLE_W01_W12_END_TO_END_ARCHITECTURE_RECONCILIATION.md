# NORYX7 — Single-Cycle W01–W12 End-to-End Architecture Reconciliation

**Date:** 2026-11-25  
**Reviewed branch snapshot:** `7bc4e56cfc183e599f47c983556e0272b1cce4c9`  
**Disposition:** architecture discovery only; not freeze, implementation, integration, verification, certification or release.

## 1. Scope and evidence rules

This is one concurrent cross-workstream cycle. It reconciles authority, runtime, state, agents, routing, evidence, simulation, surfaces, security, qualification, infrastructure and public impact. Findings distinguish observed source behavior, architecture requirements and unknowns from bounded inspection. A failed/absent bounded lookup is not a repository-wide absence claim.

No executable source, tests, workflows, dependencies, configuration, deployment files or frozen baseline were changed.

## 2. Source anchors inspected

All paths below were fetched from the branch named above. Blob SHAs:

| Path | Blob SHA |
|---|---|
| `core/identity.py` | `e6e8e5b03135251baca489643f86c7d81a755a08` |
| `core/multiauth.py` | `885e6d64f91d300dc6ee3de74b116e59dca324c1` |
| `core/attestation.py` | `48a5145b33c73c9e8d3b1f0051050dd97f89786f` |
| `core/key_lifecycle.py` | `9cdb83a93dc75df6b1fc9041f75894cf960328a5` |
| `core/authorization_replay.py` | `52c1e3ed706b48e9ffc97f34e6b8b07c7eeed1db` |
| `core/recovery.py` | `226193d08b0b8c57f275125e25b7823886ea163d` |
| `core/state.py` | `f1dd791359038d799a63852ea850ce7f3d738148` |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` |
| `noryx7_runtime/state.py` | `444aba1fb92a4bb70ee2ee31b23d3946680bb630` |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` |
| `core/coordination.py` | `c5743872a5b50765db04e4a42739e9ad238ad983` |
| `core/agent_mesh.py` | `25c9162750708e53742862f9f413fdf5200ca08f` |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` |
| `core/resource_router.py` | `4f7bf28200edd05f1236d9779437e4aa43bba8ab` |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` |
| `core/universal_intelligence.py` | `986dd5976b6451a5a75950535c13f4355f57fb0f` |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` |
| `ecosystem/runtime_dispatch.py` | `9f4f628c322aabb571fce64d54c3d6740cb142fd` |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` |

The previous source reconciliation also maps `web/app.py`, `gateway/auth.py`, `gateway/server.py`, `gateway/runtime_adapter.py`, runtime lifecycle and scheduler. FastAPI `/v1/execute` uses gateway session verification; `/api/chat` directly invokes runtime; a separate gateway server exposes gateway routes. External proxy equivalence is unknown. This cycle does not claim exhaustive dynamic caller/constructor coverage.

## 3. Cross-workstream invariants required before freeze

1. One logical issuer/owner per authority; local registries are projections or enforcement points.
2. One parent execution identity propagates through child steps, provider attempts, effects, attestations and commits.
3. Execution status, transport outcome, target effect certainty, verification and durable commit are distinct.
4. Authorization binds principal, tenant, device/workload, exact action/target/payload digest, capability, policy epoch, expiry and replay identity.
5. No blind retry after uncertain external effects; retry depends on target idempotency and effect certainty.
6. Source observation, signed origin, structural verification, formal proof, simulation, calibrated prediction and field observation are distinct evidence classes.
7. Every journal/store/outbox/replica/ledger defines writer, reader, transaction, integrity, retention, deletion, recovery and acknowledgement.
8. Placement preference is not a capacity lease, reservation, residency enforcement or worker attestation.
9. Role/skill registration is not specialist qualification or jurisdictional authority.
10. Financial, reputation and impact records cannot issue runtime capabilities.
11. Offline mode has explicit revocation freshness, epoch, monotonicity, durable queue and uncertain-effect semantics.
12. CI, artifact provenance, release promotion and production readiness are separate evidence records.

## 4. W01–W12 concurrent disposition

| Stream | Observed source boundary | Required architectural closure |
|---|---|---|
| **W01 Identity** | IdentityRegistry, SignedApprovalAuthority, RuntimeIdentity, gateway sessions and GlobalIdentityAuthorizationFabric are distinct local abstractions. | Canonical principal/issuer hierarchy; tenant/device/workload binding; delegation; capability issuance; bootstrap; revocation propagation; key epochs and freshness. |
| **W02 Runtime** | RuntimeEngine owns local authorization/reservation/dispatch/verification/attestation/commit; API and gateway ingress paths differ. | Canonical ingress; parent/child IDs; cancellation/deadline; attempt identity; effect uncertainty; compensation; commit ordering and long-running jobs. |
| **W03 Memory/state** | Runtime StateJournal is in-memory reservation/attestation; core StateJournal is SQLite verified-state persistence; StateStore optionally uses it; GlobalMemoryFabric is an in-process index. | Distinct journal roles under one commit/recovery protocol; tenancy; replica consistency; tombstones; backup expiry; key rotation and external-effect reconciliation. |
| **W04 Agents** | AgentMesh chooses lexical-first role match; AgentCoordinator truncates to `max_agents`, creates a new execution ID and executes sequentially. | Qualified selection; parent-bound DAG; branching/merge; cancellation; partial joins; dissent; verifier independence; fairness and capacity. |
| **W05 Routing** | ProviderRouter retries on exceptions; ProviderExecutionGateway selects one provider; ResilientProviderExecutor has separate bounded retries; ResourceRouter uses static thresholds. | One retry/effect owner; idempotency; timeout semantics; live health/capacity; residency; budget/energy; placement leases. |
| **W06 Evidence** | VerificationEngine performs shape/presence and identity checks; evidence structures carry source/claim/strength; signatures prove scoped origin/integrity, not truth. | Source-span custody; authority/time validity; claim graph; contradiction lifecycle; proof-checker trust; calibration; executed campaign and independent verifier lineage. |
| **W07 Simulation** | CyberRange is synthetic/sandbox-scoped; InternalSimulator was previously found to be structural, not calibrated domain simulation. | Model manifest; calibration/validation; assumptions; uncertainty/OOD; reproducibility; safety envelope; simulation-to-reality admission. |
| **W08 Surfaces** | MediaRef binds modality/type/digest/locator, not complete custody/consent; offline queue is in-memory; multiple gateway/web surfaces exist. | Shared surface identity; device enrollment; browser/effect isolation; media lineage; consent/retention; durable outbox/inbox; clock rollback and conflict reconciliation. |
| **W09 Security** | Ed25519 identity, signed approvals, attestation interface, key metadata, secure-channel replay defense, bounded replay guard and recovery epoch are local controls. | Trust-root hierarchy; signer roles/epochs; KMS/HSM lifecycle; compromise response; fleet revocation; durable replay; runtime measurement; egress and signed release chain. |
| **W10 Domains** | Role/skill and assessment structures do not prove competence, jurisdiction, currency or independence; domain assurance specifies 13 packages. | Qualification authority; credential provenance; scope/jurisdiction/expiry; conflicts; suspension; reviewer independence and calibration. |
| **W11 Global ops** | GlobalControlPlane/CellRegistry/ElasticComputeFabric are in-process models; placement is heuristic; supply-chain signature check is not a complete release process. | Durable control plane; scheduler leases; brokers/storage; SLOs; incident response; backup/restore; region failover; canary/rollback and energy accounting. |
| **W12 Economy/impact** | BUSINESS_PROJECT_FABRIC specifies separate customer/third-party/company ledgers and authorized transaction adapters; Domain Assurance specifies public-interest D13. Production ledger/payment/audited impact pipeline not established by this bounded source pass. | Double-entry invariants; fund segregation; escrow/custody; payments/disputes; commission versioning; worker safeguards; consent/grievance; baseline/counterfactual/additionality/leakage/rebound/permanence and independent measurement. |

### Required canonical objects

- **W01:** PrincipalAssertion, DelegationGrant, CapabilityDecision.
- **W02:** ParentExecution, StepInvocation, ActionAuthorization.
- **W03:** ActionReservationJournal, AttestationJournal, VerifiedStateCommitStore, MemoryRecordStore.
- **W04:** AgentSelection, DelegationLease, BranchLineage, DissentRecord.
- **W05:** ProviderDispatchPlan, DispatchAttempt, IdempotencyKey, PlacementLease.
- **W06:** EvidenceRecord, ClaimRecord, ProofRecord, EvaluationExecution.
- **W07:** SimulationRun, ModelManifest, CalibrationRecord, RealityBridgeApproval.
- **W08:** SurfaceSession, DeviceAttestation, MediaCustodyRecord, OfflineSnapshotLease, DurableOutboxReceipt.
- **W09:** TrustBundle, KeyEpoch, RevocationStatement, RuntimeMeasurement, RecoveryAuthorization.
- **W10:** DomainQualification, ScopeGrant, ReviewerIndependenceRecord.
- **W11:** CapacityReservation, WorkloadPlacementLease, ServiceHealthEvidence, ReleaseEvidence, IncidentRecord.
- **W12:** FinancialEntry, TransactionReceipt, ImpactEvidence, GovernanceDecision.

Each object must define owner, issuer/writer, readers, persistence, integrity, lifecycle, expiry, deletion, recovery and cross-boundary rules. Shared ID strings do not imply shared authority.

## 5. Collision register

| Collision | Resolution target | Required evidence |
|---|---|---|
| Multiple identity registries | One logical issuer; projections with freshness/revocation | Constructors, writers, revokers, consumers |
| Multiple action gates | One decision schema and issuer | Issuer uniqueness, target binding, replay |
| Multiple journals/stores | Distinct roles under canonical commit/recovery | Constructors, appenders, readers, ordering, restore |
| Runtime vs external effect | Separate state machines and receipts | Adapter, timeout, exception, retry, compensation |
| Provider retry overlap | One retry/effect coordinator | All consumers and nested retry composition |
| Agent scheduling overlap | Qualified selection and parent-bound DAG | Callers, IDs, cancellation, joins |
| Evidence vs verification/audit | Typed claims and independent admission | Producer, signer, verifier, custody |
| Offline vs online trust | Durable queue and revocation/epoch semantics | Persistence adapter, reconnect ack, local effects |
| Global placement vs static routing | Lease/reservation and live capacity | Scheduler/worker adapters |
| Specialist label vs qualification | Evidence-backed scoped qualification | Issuer, expiry, suspension, independence |
| CI vs release/readiness | Separate evidence and promotion policy | Artifact provenance, environment, approval |
| Ledger vs runtime authority | Separate financial custody and capability planes | Ledger writer, transaction authorization, audit |

## 6. Linked lifecycles

Execution/evidence: `DISCOVER → AUTHENTICATE → AUTHORIZE → PLAN → DELEGATE → SCHEDULE → DISPATCH → OBSERVE → VERIFY → ATTEST → COMMIT → AUDIT`.

External effect: `NOT_DISPATCHED → DISPATCHING → ACCEPTED / REJECTED / UNKNOWN → OBSERVED / NOT_OBSERVED → RECONCILED`.

A timeout or exception after dispatch can leave an effect UNKNOWN. It must not be interpreted as no effect without target evidence. A dispatch receipt is not proof of target effect; a state commit is not proof that an external effect occurred.

## 7. Parallel closure and acceptance

All streams continue discovery in parallel. Shared-contract acceptance follows upstream ownership:
- Foundation authority/custody: W01 + W03 + W09, with W06 evidence identity.
- Execution/coordination: W02 + W04 + W05.
- Surfaces/simulation: W08 + W07.
- Domain/public impact: W10 + W12.
- Global operations: W11 integrates capacity, release, observability and recovery.

This is dependency-aware acceptance, not a serial implementation schedule.

Each stream remains PARTIAL until its scoped inventory, constructors/registrations/callers/readers/writers, ownership, versioned contracts, failure/retry/recovery/deletion/revocation semantics, accepted handoffs and traceability are documented. Implementation, verification, release and operational readiness remain separate statuses.

## 8. Disposition and next source pass

- W01–W12 remain **PARTIAL**; none is promoted to DECIDED or FROZEN.
- Existing ADRs are not silently accepted, superseded or renumbered. No new ADR series is created here.
- Next pass must exhaust constructor/registration/call-site mapping for identity, ActionGate, replay, both journals, all ingress/deployment middleware, provider consumers, agent-fabric consumers, offline persistence adapters, W12 ledger/payment/impact paths and release configuration.
- No implementation, integration, test campaign, merge, deployment or architecture freeze is authorized.
