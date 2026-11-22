# NORYX7 — Architecture Open Decisions and Closure Backlog

**Status:** architecture decision register; unresolved items are deliberately not guessed  
**Parent:** System-Wide Architecture Closure Blueprint  
**Rule:** this backlog is design work only. It does not authorize code integration, test campaigns, merge or deployment.

## 1. Priority model

- **B0 — Blocking:** must be resolved before architecture freeze because it affects authority, trust, state ownership or a shared schema.
- **B1 — High:** must be resolved before the dependent workstream can freeze.
- **B2 — Medium:** can be frozen with an explicit deferred capability and owner.
- **B3 — Later:** product/domain expansion that does not block the common substrate.

## 2. Blocking decisions

| ID | Priority | Decision to resolve | Affected planes | Required evidence/output |
|---|---|---|---|---|
| ADR-B01 | B0 | Canonical authority map across Identity, Policy, Capability Broker, ActionGate and Runtime | P06–P13 | One authority sequence, issuer/consumer matrix and revocation semantics |
| ADR-B02 | B0 | Canonical runtime/lifecycle ownership across core runtime, operational runtime, HYPERSYNTH runtime, JARVIS runtime and `noryx7_runtime` | P03–P10, P12 | Runtime ownership diagram, state machine, facade/adapter map, deprecation rules |
| ADR-B03 | B0 | Canonical state, journal, attestation and commit ownership across core, runtime and JARVIS | P09–P16 | One state authority model, transaction boundaries, replay/rollback and recovery contract |
| ADR-B04 | B0 | Canonical agent identity, delegation and supervisor lifecycle | P03, P05–P08, P10–P11 | Agent lifecycle, trust registration, delegation attenuation, revocation and result admission |
| ADR-B05 | B0 | Shared provenance/evidence model across NEXUS, Universal Intelligence, memory, simulation and audit | P03, P09, P15, P18 | Claim/evidence/source schema, epistemic states, lineage and conflict model |
| ADR-B06 | B0 | Tenant/principal/session/data-scope model across JARVIS, API, memory, tools and distributed nodes | P01–P14 | Identity graph, tenant isolation matrix, session binding and data-flow map |
| ADR-B07 | B0 | One dependency and compatibility policy for schemas, vocabularies, contracts and runtime envelopes | P01–P18 | Versioning policy, compatibility classes, migration and unknown-field rules |
| ADR-B08 | B0 | Offline revocation freshness and action restrictions during partition | P05, P07, P10–P13, P16 | Offline trust epoch, maximum staleness, forbidden action classes and reconciliation |

## 3. High-priority architecture decisions

| ID | Priority | Decision to resolve | Affected planes | Required evidence/output |
|---|---|---|---|---|
| ADR-H01 | B1 | NEXUS-IR semantic type/ontology ownership, canonicalization and vocabulary governance | P01–P06, P09, P18 | Normative schema model, canonicalization profile, ontology release lifecycle |
| ADR-H02 | B1 | NEXUS-Wire message envelope, transport-independent framing, replay/expiry and compatibility | P06–P14 | Wire envelope, identity binding, version negotiation and transport matrix |
| ADR-H03 | B1 | FRL proof artifact and checker trust model; distinction from empirical and simulation evidence | P03, P09, P15, P18 | Exact proposition/theory/checker identity and result semantics |
| ADR-H04 | B1 | MIRROR WORLD common world graph, scenario lifecycle, simulation kernel interfaces and fidelity dimensions | P03–P05, P08–P10, P13, P18 | World/scenario schema, experiment manifest, kernel contract and calibration lifecycle |
| ADR-H05 | B1 | Reality Bridge policy and safety case for any simulation-to-real operation | P07–P16 | Isolated trust zone, allow-list, approval, rollback and audit contract |
| ADR-H06 | B1 | Browser-to-JARVIS/NORYX7 future bridge and Browser version boundary | P14 | User gesture, origin, target, capability, content exposure and revocation contract |
| ADR-H07 | B1 | Model/provider routing versus node/resource placement responsibilities | P05, P10, P13, P17 | Two-stage route model and explicit handoff contract |
| ADR-H08 | B1 | Memory tier ownership, source lineage, deletion, expiry and replica tombstones | P09, P12, P13, P15 | Memory lifecycle, retention/deletion matrix and restore behavior |
| ADR-H09 | B1 | Key custody and root-of-trust bootstrap across device, edge, cloud and recovery | P11–P16 | Key hierarchy, platform KMS/keystore boundary, compromise/recovery model |
| ADR-H10 | B1 | Audit chain versus diagnostic telemetry versus business ledger | P12, P15, P17 | Event classes, retention, integrity and independent access policies |
| ADR-H11 | B1 | Shared result semantics for accepted, rejected, partial, indeterminate, unsupported, degraded, failed and quarantined | P03–P18 | Outcome schema and transition matrix |
| ADR-H12 | B1 | Global resource budgets, scheduling fairness and high-risk workload priority | P05–P10, P13, P17 | Budget taxonomy, admission, preemption, backpressure and SLO model |

## 4. Medium-priority decisions

| ID | Priority | Decision to resolve | Affected planes | Required evidence/output |
|---|---|---|---|---|
| ADR-M01 | B2 | Multimodal source coordinate and temporal alignment schema | P01–P03, P09, P18 | Frame/sample/span addressing and transformation lineage |
| ADR-M02 | B2 | Systems reverse-engineering scope, evidence sufficiency and authorization tiers | P06–P08, P11, P14, P18 | Asset authorization manifest, passive/active scope and report standard |
| ADR-M03 | B2 | Controlled self-improvement proposal and staged release lifecycle | P03, P10–P12, P15–P16 | Immutable proposal, evaluation, approval, signed release and rollback |
| ADR-M04 | B2 | Domain package manifest, validator API and domain-specific escalation policy | P18 | Domain contract, source classes, validity and review model |
| ADR-M05 | B2 | Operator console and emergency stop separation | P14–P16 | Operator roles, break-glass, dual control and immutable audit |
| ADR-M06 | B2 | Usage metering, tenant billing and financial ledger separation | P07, P10, P12, P14–P15, P17 | Metering schema, billing authority and reconciliation |
| ADR-M07 | B2 | Localization, accessibility and consent UX requirements | P02, P14 | Surface acceptance and user-control matrix |

## 5. Deferred product/domain decisions

| ID | Priority | Decision to resolve | Affected domains |
|---|---|---|---|
| ADR-L01 | B3 | Initial Mirror World kernel sequence and supported fidelity profiles | Synthetic web, software, physical, environmental, socio-economic |
| ADR-L02 | B3 | Domain rollout sequence and expert reviewer network | Health, legal, finance, science, engineering, agriculture, ecology, education, logistics, community |
| ADR-L03 | B3 | Edge hardware profiles, accelerator support and power/thermal envelope | Device/Edge/Cloud |
| ADR-L04 | B3 | Multi-region residency, disaster recovery objectives and capacity model | Distribution/Operations |
| ADR-L05 | B3 | Product packaging, pricing, metering and commercial workflow scope | Business/Project Fabric |

## 6. Closure sequence

1. Resolve B0 decisions first; no dependent contract can be frozen while authority/state/identity semantics conflict.
2. Resolve B1 in parallel after B0 owners and vocabulary are fixed.
3. Mark B2 as either resolved or explicitly deferred with rationale and owner.
4. Convert each decision into an ADR with alternatives, consequences, affected paths and migration notes.
5. Update the architecture index and traceability ledger after each accepted decision.
6. Freeze only when all B0 and B1 items are resolved and every B2/B3 item has an explicit disposition.

## 7. Freeze gate checklist

- [ ] All 18 canonical planes have contract cards and exact source traceability.
- [ ] Cross-cutting domains map to canonical plane owners.
- [ ] No conflicting authority, runtime, state or recovery owner remains.
- [ ] Every external side effect has one authorization path and one result-admission path.
- [ ] Every persistent data class has purpose, retention, deletion and replica rules.
- [ ] Every distributed/offline mode has identity, revocation and replay semantics.
- [ ] NEXUS, FRL and MIRROR WORLD schemas and trust boundaries are mutually consistent.
- [ ] Browser v0.1 isolation and future bridge are explicitly separated.
- [ ] Failure, cancellation, expiry, degradation and recovery semantics are complete.
- [ ] Resource budgets and SLO measurement boundaries are defined.
- [ ] Domain-specific escalation and human-control requirements are explicit.
- [ ] Compatibility, migration, rollback and deprecation are documented.
- [ ] Implementation and verification status are separate and evidence-backed.
- [ ] All unresolved decisions have owners and explicit dispositions.

**Current disposition:** architecture closure remains in progress. This register identifies the next design work and must not be interpreted as an approval to begin integration.

## 8. New architecture decision records — 2026-11-21

| ADR | Decision area | Current state | Remaining evidence |
|---|---|---|---|
| ADR-002 | Canonical runtime topology and facade ownership | Proposed; source anchors inspected | Full call-site/constructor inventory; JARVIS lifecycle mapping; compatibility matrix |
| ADR-003 | State/journal/commit/recovery authority | Proposed; core and operational journal anchors inspected | Complete persistence inventory; namespace and cross-journal saga rules; recovery matrix |
| ADR-004 | Agent fabric, delegation and result admission | Proposed; native and operational fabric anchors inspected | All direct invocation paths; registry/key lifecycle; independent-review guarantees |
| ADR-005 | Provider/agent/scheduler/placement separation | Proposed; router and deterministic scheduler anchors inspected | ResourceRouter and model-fabric responsibility map; budget enforcement locations |

## 9. Workstream status and next closure pass

The parallel workstream map is maintained in [NORYX7_PARALLEL_ARCHITECTURE_WORKSTREAMS.md](NORYX7_PARALLEL_ARCHITECTURE_WORKSTREAMS.md). Current work is **SOURCE-RECONCILED in part**, not DECIDED or FROZEN. ADR-002 through ADR-005 are proposals pending the acceptance evidence listed in each ADR.

Next architecture-only pass:
1. Complete the call-site inventory for all runtime entry points and JARVIS surfaces.
2. Map every durable state/journal implementation, namespace and recovery consumer.
3. Trace every direct agent invocation and result-admission path.
4. Separate model/provider routing from resource placement in the actual source inventory.
5. Resolve W01 authority/identity and W06 semantic/evidence contracts before declaring dependent streams frozen.

No implementation, integration, test campaign, merge or deployment is authorized by these records.


## 10. Source-reconciliation decisions discovered in W01–W05

| ID | Priority | Decision | Source-grounded reason | Required closure evidence |
|---|---|---|---|---|
| ADR-B09 | B0 | Canonical identity/trust-root authority across in-memory and durable registries | core/identity.py provides an in-memory agent-key registry; durable principal/agent binding work exists separately | Full registry inventory, issuer matrix, root bootstrap/recovery, rotation/revocation and offline freshness |
| ADR-B10 | B0 | Canonical runtime entrypoint and facade ownership | NORYXRuntime, HypersynthRuntime and OperationalNORYXRuntime overlap in orchestration/lifecycle | Constructor/call-site graph, JARVIS/runtime adapters, startup/shutdown and migration contract |
| ADR-B11 | B0 | State, audit and external witness namespace/recovery boundaries | StateStore/StateJournal provide local verified commits and a SQLite digest journal; audit/external witness are separate concerns | All journal consumers, namespace matrix, recovery-point and side-effect saga semantics |
| ADR-B12 | B0 | Canonical agent dispatch and mandatory result admission | AgentFabric directly invokes AgentCore.run; OperationalAgentFabric routes through AgentSupervisor | All direct invocation paths, identity/lease checks, selected-agent binding and admission contract |
| ADR-B13 | B1 | Composed provider retry/failover and placement policy | ProviderRouter retries on exceptions; ProviderExecutionGateway and ResilientProviderExecutor add separate layers; ResourceRouter is a separate tier heuristic | Unified retry/idempotency budget, provider trust/residency/cost constraints, capacity reservation and placement contract |
| ADR-B14 | B1 | Canonical approval semantics for structural vs signed multi-authorization | core/multiauth.py retains a legacy structural AuthorizationProof alongside SignedAuthorizationProof | Call-site inventory and proof-type acceptance matrix proving privileged paths require signed approvals |

These are newly discovered decisions, not resolved findings. Do not interpret the presence of a source implementation as satisfying the decision.


## 11. Source-reconciliation decisions discovered in W06–W12

| ID | Priority | Decision | Source-grounded reason | Required closure evidence |
|---|---|---|---|---|
| ADR-B15 | B0 | Canonical evidence/provenance and semantic schema | Current typed Evidence/DomainAssessment and VerificationResult are not a complete shared semantic/provenance graph | NEXUS schema, source coordinates, temporal validity, independence, transformation lineage and conflict semantics |
| ADR-B16 | B1 | Offline snapshot issuer, monotonic anchor and conflict authority | Offline module defines protocols/states but concrete implementations and caller wiring require mapping | Issuer/signature, policy epoch, anti-rollback, queue durability, idempotency and conflict/reconciliation contract |
| ADR-B17 | B1 | MIRROR WORLD fidelity and Reality Bridge authority | CyberRange is synthetic/sandbox scoped; wider world models require independent calibration and bridge gates | World-type/fidelity manifest, calibration evidence, isolation and human authorization contract |
| ADR-B18 | B1 | Supply-chain root and release provenance authority | SecureBootChain and SupplyChainVerifier exist as separate source components | Root provisioning, build attestation, dependency/model manifests, revocation and rollback contract |
| ADR-B19 | B1 | Durable distributed memory and identity fabric boundary | GlobalMemoryFabric and GlobalIdentityAuthorizationFabric are explicitly in-memory indexes with adapters externalized | Durable store/transport/replication adapters, consistency, tenant isolation, deletion and canonical authority mapping |
| ADR-B20 | B1 | Fleet operations, alert delivery and service-level objectives | Local event bus/alert router/runtime limits do not establish fleet-wide operational guarantees | SLO tiers, delivery/acknowledgement, telemetry retention, overload, incident and DR evidence |
| ADR-B21 | B2 | Domain package manifest and expert governance per specialist domain | Domain routing exists but does not prove complete domain-specific validity controls | Ontology, accepted sources, jurisdiction, units, uncertainty, exclusions and escalation owner for each domain |


## 12. Additional source-grounded blocking decisions — deep reconciliation

| ID | Priority | Decision | Source-grounded reason | Required closure evidence |
|---|---|---|---|---|
| ADR-B22 | B0 | Relationship between CanonicalSystemFabric, SRC, RuntimeEngine and ExecutionFabric | Separate composition/execution abstractions coexist; hierarchy not established | Complete constructor/call-site graph; one lifecycle owner and no shadow dispatch path |
| ADR-B23 | B0 | Recovery/defense/authorization epoch coordination | RecoveryController, defense mode, authorization epoch and offline anchor are distinct | Transition matrix, epoch owner, crash consistency and rollback-resistant persistence |
| ADR-B24 | B0 | Durable idempotency reservation at dispatch boundary | Runtime StateJournal reservations are in-memory; core SQLite journal is separate | Durable reservation backend, atomicity, retention, cross-process semantics and uncertain-side-effect handling |
| ADR-B25 | B1 | AgentMesh/AgentRuntime/AgentCoordinator/AgentFabric responsibilities | Mesh, liveness, coordination, direct dispatch and operational supervision are separate components | Full invocation graph, role/skill/capability semantics, leases and independent consensus evidence |
| ADR-B26 | B1 | Actual egress and execution-adapter enforcement point | EgressPolicy is an in-memory allowlist; ExecutionFabric has a separate authorization callback | Network-level enforcement, DNS/redirect handling, policy distribution and revocation |
| ADR-B27 | B1 | Production monotonic anchor and offline trust root | SQLite anchor explicitly requires protected storage or hardware-backed replacement in production | Hardware/storage trust model, issuer, anti-rollback, recovery and freshness policy |
| ADR-B28 | B1 | Structural completeness versus architecture freeze acceptance | architecture_registry structural gate cannot prove complete callers/deployment/operational readiness | Evidence-backed freeze gate with separate architecture and implementation status axes |
| ADR-B29 | B1 | Deployment and operations source of truth | CI workflow inventory exists, but deployment/infra root directories were not found in the inspected root | Explicit deployment inventory, runtime environments, secrets, artifact promotion, backup and DR |


## 13. Polyglot/JARVIS/mobile/deployment decisions

| ID | Priority | Decision | Source-grounded reason | Required closure evidence |
|---|---|---|---|---|
| ADR-B30 | B0 | JARVIS dual-policy and identity authority semantics | JarvisRuntime checks user grants in JARVIS Policy and then uses a generated JARVIS agent identity plus core ActionGate/AuthorizationAuthority | Principal/agent matrix, policy order, grant revocation and audit correlation |
| ADR-B31 | B0 | Cross-store JARVIS/RuntimeEngine transaction semantics | JARVIS request reservation/commit and RuntimeEngine step reservations/attestation journal are distinct | Saga/recovery contract across request reservation, step reservation, attestation append and final commit |
| ADR-B32 | B1 | JARVIS workload identity/key lifecycle | JarvisRuntime generates its JARVIS agent identity at construction | Durable identity issuer, key custody, restart, rotation, revocation and recovery |
| ADR-B33 | B1 | Polyglot service maturity and canonical wire contracts | Go gateway and Rust runtime library currently provide health/digest and envelope digest/deny helper surfaces, not the full Python runtime | Role/maturity matrix, shared schemas, digest/signature semantics and compatibility rules |
| ADR-B34 | B1 | Mobile/browser device trust and bootstrap credential lifecycle | iOS local grants/replay, Android audio interface and Browser bootstrap/session client are distinct local boundaries | Device enrollment, secret storage, session revocation, hardware trust and platform capability boundary |
| ADR-B35 | B1 | Multi-artifact deployment and release authority | Render config describes one Python service while repository also contains Go/Rust/mobile/browser artifacts | Artifact catalog, build provenance, signed promotion, secrets, rollback, observability and DR |


## 7. New decisions from parallel W06–W12 expansion — 2026-11-22

| ID | Priority | Decision to resolve | Affected streams/planes | Required evidence/output |
|---|---|---|---|---|
| ADR-B36 | B0 | NEXUS-IR/Wire canonical schema, canonicalization and cross-language semantic compatibility | W06, W01–W05, W08 | Normative schemas, canonicalization profile, compatibility and migration matrix |
| ADR-B37 | B0 | Evidence ontology and epistemic-state transitions across source, observation, inference, proof, empirical and simulation results | W06, W07, W09, W10 | Typed evidence registry, lineage, validity scope, contradiction and expiry rules |
| ADR-B38 | B1 | FRL checker trust, proof replay and formal/empirical/simulation separation | W06, W07, W09 | Trusted checker/kernel model, artifact contract and bounded verification semantics |
| ADR-B39 | B1 | MIRROR WORLD world/scenario/model registry, calibration, holdout and fidelity governance | W07, W06, W10, W11 | Domain world manifests, calibration evidence, holdout custodian and drift policy |
| ADR-B40 | B0 | Reality Bridge separation and real-world actuation safety case | W07, W01–W05, W09 | Independent real authority, approved action taxonomy, human approval, rollback and audit |
| ADR-B41 | B1 | Domain Manifest governance and qualified human escalation | W10, W06, W09, W12 | Per-domain source standards, jurisdiction, review qualifications, prohibited use and appeal |
| ADR-B42 | B1 | Multi-artifact release, SLO, observability, backup/restore and incident source of truth | W11, W02, W08, W09 | Signed artifact catalog, deployment topology, measured SLOs, DR and incident runbooks |
| ADR-B43 | B1 | Tenant, marketplace, payment, contribution, governance and impact-ledger boundaries | W12, W01, W06, W09–W11 | Legal entity/jurisdiction model, ledger separation, dispute rights, safeguarding and impact assurance |

These are open decisions, not accepted ADRs. They do not authorize implementation or integration.


## 8. W01–W05 and shared cognitive substrate decisions — 2026-11-22

| ID | Priority | Decision to resolve | Affected streams/planes | Required evidence/output |
|---|---|---|---|---|
| ADR-B44 | B0 | Human, tenant, workload, agent, device, session and execution identity taxonomy and issuer graph | W01–W04, W08, W09 | Canonical principal and grant contracts |
| ADR-B45 | B0 | Cross-front request/task/step/execution/action/idempotency/correlation identity lifecycle | W01–W03, W08 | Versioned lifecycle envelope and state-transition owner |
| ADR-B46 | B0 | Canonical agent topology, scheduler and parallel DAG execution semantics | W02, W04, W05, W11 | Ownership map, DAG, concurrency/failure/cancel contract |
| ADR-B47 | B0 | Canonical memory classes, stores, retention, provenance and deletion/tombstone semantics | W03, W06, W08–W12 | Storage authority and memory record contract |
| ADR-B48 | B1 | Provider selection, execution authorization, failover and indeterminate retry semantics | W02, W05, W08, W09, W11 | Route contract and retry state machine |
| ADR-B49 | B1 | Device/edge/cloud placement with privacy, jurisdiction, capacity, cost and energy constraints | W05, W08, W11 | Placement request/result contract |
| ADR-B50 | B0 | HYPERSYNTH evidence/verification semantics and calibration of confidence outputs | W06, W07, W09, W10 | Typed result/evidence classes and calibrated uncertainty policy |
| ADR-B51 | B1 | Multimodal media locator, security, consent, retention and transformation lineage | W06, W08, W09, W10 | Media manifest and isolated processing contract |
| ADR-B52 | B1 | User-understanding consent, profile lifecycle, correction and deletion | W03, W08, W09, W12 | Consent ledger, derived-data lineage and profile expiry |
| ADR-B53 | B1 | Self-improvement external admission, protected zones and rollback authority | W07, W09, W11 | Signed proposal/release/rollback contract |
| ADR-B54 | B0 | Offline outbox, durable dispatch reservation and commit/reconciliation atomicity | W02, W03, W08, W09, W11 | Transactional outbox/inbox and idempotency protocol |
| ADR-B55 | B0 | Four-front dispatch ownership and canonical runtime lifecycle hierarchy | W01, W02, W04, W08 | One lifecycle owner and explicit compatibility adapters |

These are open decisions, not accepted ADRs. They do not authorize implementation or integration.


## 9. Runtime and repository inventory decisions — 2026-11-22

| ID | Priority | Decision to resolve | Affected streams | Required output |
|---|---|---|---|---|
| ADR-B56 | B0 | RuntimeEngine lifecycle states for indeterminate side effects, partial results and compensation | W02, W03, W08, W09, W11 | Canonical outcome/state-transition matrix |
| ADR-B57 | B0 | Topological ordering vs actual parallel execution and bounded scheduler ownership | W02, W04, W05, W11 | Concurrency, dependency and cancellation contract |
| ADR-B58 | B1 | ModelFabric keyed attestation requirements and mandatory runtime binding | W01, W05, W06, W09 | Model result trust profile and key lifecycle |
| ADR-B59 | B1 | Provider usage/cost/latency metering and stale metadata handling | W05, W11, W12 | Metering contract and provider reconciliation |
| ADR-B60 | B0 | Route-level API authentication and equivalence between /api/chat and /v1 gateway routes | W01, W02, W08, W09 | Endpoint inventory, principal source and authorization matrix |
| ADR-B61 | B1 | CI coverage for iOS adapter and explicit per-artifact release evidence | W08, W11 | Platform verification/release coverage matrix |
| ADR-B62 | B1 | Architecture audit scripts: scope, completeness claims and machine-readable evidence schema | W02, W06, W11 | Audit evidence contract and limitations |

These decisions remain open. They do not authorize implementation or tests.

## Additional decisions — 2026-11-22

### B63 — Canonical ingress and route authentication parity
**Streams:** W01, W08, W09. Decide one explicit authentication/authorization boundary for every FastAPI, gateway, browser and future surface route. Record route-by-route enforcement, trusted proxy assumptions, principal resolution, rate limits and failure behavior. The direct `/api/chat` route and session-authenticated `/v1/execute` route are not equivalent in the inspected source; external middleware must be evidenced rather than assumed.

### B64 — Context and observation evidence envelope
**Streams:** W01, W06, W08. Define source/device identity, issuer, tenant, classification, purpose/consent, capture time, monotonic sequence, payload digest, calibration, freshness, signature/attestation, retention and revocation. Callback authorization and caller-supplied timestamps alone do not authenticate evidence.

### B65 — Device enrollment, attestation and lease lifecycle
**Streams:** W01, W08, W09. Decide hardware/workload identity, secure enrollment, attestation freshness, capability version, lease/fencing, disconnect behavior, remote revocation and recovery. An in-memory first-capable-device lookup is not a trusted fleet selector.

### B66 — Cyber-range authorization and Reality Bridge gate
**Streams:** W06, W07, W09. Define signed owner authorization bound to target, scenario, technique/action digest, expiry, policy epoch and revocation. Preserve synthetic-only simulation by default; any real-world bridge is a separate privileged, human-reviewable operation with independent policy and audit.

### B67 — Global capacity reservation and durable delivery
**Streams:** W05, W08, W11. Define atomic resource reservation, lease expiry, fencing token, idempotent release, capacity epoch, durable queue, delivery guarantees, deduplication, poison-message quarantine, retry/backpressure and reconciliation. In-memory registries and queues are not production global scheduling.

### B68 — Consent, profile lineage and deletion propagation
**Streams:** W01, W06, W12. Define purpose-specific consent receipts, raw/derived data separation, inference provenance, correction/supersession, retention, tenant isolation, deletion/tombstone propagation and audit. Personalization signals must not become authorization evidence by implication.

### B69 — Canonical provider capability and usage contract
**Streams:** W05, W09, W11. Define provider/model identity, typed capability schemas, structured proposal parsing, ActionGate handoff, privacy/residency, timeout/cancellation, idempotent retry, usage/cost/latency evidence, circuit state and external receipt verification. Model reasoning, adapter availability, authorization and execution remain separate authorities.
