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

## Additional decisions — 2026-11-23

### B70 — Durable security event and incident response contract
**Streams:** W09, W11. Define authenticated event producers, stable event/correlation IDs, trusted time/sequence, signed evidence references, durable append/ack/replay, retention, tenant partitioning, loss/backpressure and incident ownership. Separate detection, alerting, declaration, containment, evidence preservation, recovery authorization and post-incident review.

### B71 — Enforced egress and bypass-path closure
**Streams:** W09, W11, W08. Decide the mandatory mediation point for every network-capable adapter and platform process. Bind authorization to resolved destination/service identity; define DNS/CNAME/rebinding, redirects, proxies, TLS, IPv4/IPv6, rule distribution, emergency revocation and proof that no direct socket bypass remains.

### B72 — End-to-end artifact and release attestation
**Streams:** W09, W11, W08. Define source commit, SBOM, builder provenance, reproducibility evidence, artifact digest, platform compatibility, independent signer quorum, key custody/rotation/revocation, staged promotion, health gates, rollback and decommission for all Python/Go/Rust/mobile/browser/model/configuration artifacts.

### B73 — Offline snapshot authenticity and trust root
**Streams:** W03, W08, W09. Define signed/MACed snapshot, issuer, key ID, device/tenant binding, policy epoch, bounded capability lease, revocation freshness, hardware monotonic root, fallback assurance level and protected backup/restore.

### B74 — Durable offline delivery and indeterminate reconciliation
**Streams:** W03, W08, W11. Define persistent outbox/inbox, deduplication, delivery guarantee, receipt, fencing, retry budget, conflict/quarantine and unknown external outcome. No blind retry after a possibly completed external side effect.

### B75 — Semantic evidence and simulation assurance levels
**Streams:** W06, W07, W10. Separate structural checks, deterministic constraints, sandbox execution, calibrated physical/numerical simulation, empirical validation, causal inference and expert judgment. Define uncertainty, calibration, holdouts, OOD limits and permitted claim strength.

### B76 — Domain specialist qualification and validity
**Streams:** W06, W10. Define domain manifest, qualification basis, scope/jurisdiction, authoritative sources, methods, reviewer requirements, conflict/uncertainty escalation, prohibited autonomous decisions, incident/liability owner and withdrawal/update process.

### B77 — Evidence-backed architecture freeze manifest
**Streams:** W01, W02, W11. Define a freeze gate separate from path-existence/structural completeness. Require exact source symbols/call sites, entrypoints, authority ownership, deployment mapping, data lifecycle, failure/recovery, resource/SLO assumptions, acceptance evidence owner and explicit UNKNOWN/deferred classification.

### B78 — Independent self-improvement admission and protected zones
**Streams:** W09, W11. Define protected trust roots, policy, audit and recovery zones; immutable proposal evidence; independent reviewer/approver; signed release provenance; canary, rollback and separation of proposer/verifier/release authority.

## Additional decisions — 2026-11-23 (four fronts, memory and ecosystem)

### B79 — Canonical front-to-principal resolution
**Streams:** W01, W02, W08. Define the trusted issuer path for user/workload/agent/device/session identity across JARVIS, Browser, HYPERSYNTH and Orchestration. Prohibit default front labels (for example `front.value`) from being accepted as authenticated principal identity.

### B80 — Intent, idempotency and dispatch lifecycle identity
**Streams:** W01, W02, W03, W08. Separate intent/request IDs from idempotency keys, execution IDs, action IDs and dispatch receipts. Define accepted/started/running/completed/rejected/failed-before-effect/failed-after-effect/indeterminate/partial/compensated outcomes and receipt durability/signature.

### B81 — Global memory consistency and deletion semantics
**Streams:** W03, W06, W09, W12. Define encrypted durable content storage, verified replica identity/failure domains, consistency and stale-read rules, tenant-before-retrieval isolation, lineage, retention, deletion tombstones, backup resurrection prevention and offline reconciliation.

### B82 — Identity authorization issuer and cache freshness
**Streams:** W01, W09, W12. Define signed issuer evidence, principal/tenant/device/session binding, capability audience, expiry, policy epoch, revocation and freshness. In-memory identity/session indexes remain caches, never independent trust roots.

### B83 — Financial ledger, funds segregation and marketplace execution
**Streams:** W09, W12. Define beneficial ownership and segregated ledgers for user, third-party, company, community/restricted-purpose, commission/refund/tax flows. Require regulated/authorized payment adapters, explicit authorization, double-entry reconciliation, settlement receipt, dispute and buyer protection. Model/agent cannot move funds.

### B84 — Community governance and independently measured impact
**Streams:** W10, W12. Define membership/decision rights, quorum/appeal, conflict of interest, safeguarding, worker safety, compensation, exit/refund, transparent pooled funds and independent audit. Environmental/social outcomes require baselines, system boundaries, net-impact accounting, uncertainty and independent evidence.


## Additional decisions — 2026-11-24 (agent dispatch, runtime lifecycle and DAG semantics)

### B85 — Canonical Agent Dispatch Ownership
**Streams:** W01, W02, W04, W05, W08, W09. Define the responsibility graph and compatibility-facade rules across AgentFabric, OperationalAgentFabric, AgentCoordinator, AgentMesh, AgentRuntime, routers and RuntimeEngine. Require call-site, authority, execution and admission ownership before selecting a canonical path.

### B86 — External Side-Effect Certainty and Reconciliation
**Streams:** W02, W03, W08, W09, W11. Define indeterminate/reconciliation/partial/compensation lifecycle states, durable adapter receipts, idempotency keys, external-effect reconciliation and human escalation. FAILED must not imply no side effect after dispatch.

### B87 — DAG Execution and Capacity Semantics
**Streams:** W04, W05, W11. Distinguish topological ordering from concurrent execution. Define bounded workers, dependency barriers, resource conflicts, fairness, retry, cancellation, deadlines, partial completion and over-capacity plan semantics.

### B88 — Typed Consensus and Independence
**Streams:** W04, W06, W10. Define comparison by output type and domain, evidence independence, calibrated uncertainty, disagreement retention and expert escalation. Agent count or equal outputs alone are not universal proof.

### B89 — Structural Registry vs Evidence-Backed Freeze
**Streams:** W01, W02, W04, W06, W09, W11. Preserve the 18-plane structural gate while requiring source symbols/call sites, authority ownership, boundary enforcement, test evidence, deployment mapping and operational acceptance for freeze.

All B85–B89 are OPEN / PROPOSED, not approved or frozen.


## Additional decisions — 2026-11-24 (cognitive evidence, Mirror World and global scale)

### B90 — Evidence Class and Assurance Ladder
**Streams:** W06, W07, W10, W11. Separate structural, synthetic, independent, empirical/domain-calibrated and operational evidence. No promotion to a stronger assurance class without explicit evidence.

### B91 — Evaluation Campaign Integrity and Benchmark Governance
**Streams:** W04, W06, W09, W10, W11. Define signed immutable manifests, evaluator identity, one-result semantics, holdout secrecy, benchmark lineage, statistical power, reproducibility and independent approval.

### B92 — FINCH Temporal Forecast Qualification
**Streams:** W06, W07, W10, W11. Distinguish keyword/severity relevance and anomaly heuristics from calibrated forecasts; require temporal backtesting, base rates, confidence intervals, drift and source-quality controls.

### B93 — MIRROR WORLD Domain Model and Reality Bridge
**Streams:** W06, W07, W08, W10, W11. Require domain-specific model contracts, calibration, uncertainty, validation and non-actuating Reality Bridge approval.

### B94 — Multimodal Data Custody and Evidence Lineage
**Streams:** W03, W06, W08, W09. Define authenticated locators, encryption, tenant/consent binding, retention/deletion and transformation lineage.

### B95 — Global Fabric Production Adapter Contract
**Streams:** W02, W05, W08, W11. Define authenticated membership, durable queues, leases, reservations, replication, autoscaling, quotas, fairness and disaster recovery.

### B96 — Safe Research Egress and Provider Attestation
**Streams:** W01, W06, W08, W09, W12. Define host/IP/redirect controls, untrusted-content isolation, signed provider receipts and high-risk transaction confirmation/reconciliation.

All B90–B96 are OPEN / PROPOSED, not approved or frozen.


## ADR-B97–B101 — 2026-11-24 (OPEN / PROPOSED)

| ADR | Decision area | Required architecture decision | Status |
|---|---|---|---|
| B97 | Canonical Claim and Evidence Lineage | Claim identity/types, source-span anchoring, support/contradiction graph, temporal validity, uncertainty, independence groups, review and expiry; no truth promotion from repetition, consensus or signature alone | OPEN |
| B98 | Research Egress and Content Isolation | Mandatory destination mediation, DNS/IP/redirect controls, parser isolation, untrusted-content handling, source custody, crawl budgets and signed provider receipts | OPEN |
| B99 | Specialist Qualification and Scope | Versioned manifests, independent qualification evidence, domain/jurisdiction scope, calibration, expiry, escalation and separation from action authority; reconcile with B76 | OPEN |
| B100 | MIRROR WORLD Model Validity and Reality Transfer | Model class, assumptions, units, calibration, independent validation, uncertainty, OOD envelope and non-actuating Reality Bridge admission; reconcile with B93 | OPEN |
| B101 | Community and Environmental Outcome Accounting | Intervention baselines, net outcome boundaries, independent measurement, contributor safeguards, restricted funds, ledger separation, grievance and public reporting; reconcile with B84 | OPEN |

These proposals extend existing architecture decisions and must be reconciled before any decision is marked accepted. They do not authorize implementation or testing.


## Additional decisions from ingress/memory/offline reconciliation — 2026-11-24

| ID | Priority | Decision to resolve | Affected planes | Required evidence/output | Status |
|---|---|---|---|---|---|
| ADR-B102 | B0 | Canonical ingress principal and session lifecycle: issuer, enrolled principal/device, audience, scope, key ID, expiry, revocation epoch and execution correlation; client IDs are metadata only | P01, P06–P14 | Enrollment/session/revocation state machine and issuer/device binding | OPEN |
| ADR-B103 | B0 | Memory context isolation and degraded-state semantics: tenant/principal/task/execution scope, explicit share grants, typed hydration outcomes, provenance, consent, expiry, deletion and audit | P01, P03, P09, P12, P15 | Canonical memory access matrix and complete lifecycle | OPEN |
| ADR-B104 | B0 | Durable offline outbox and indeterminate side-effect reconciliation: persistent intent, idempotency, receipts, crash recovery, duplicate delivery, compensation and remote acknowledgement | P05–P09, P12–P16 | State machine and cross-store transaction/reconciliation contract | OPEN |

**Decision consolidation, not duplicate ADR creation:** proposed B105 (durable security events/incident lifecycle) overlaps ADR-B70; proposed B106 (evidence-backed release/self-improvement admission) overlaps ADR-B72 and ADR-B78. Reconcile their scope and acceptance evidence into those existing decisions rather than creating parallel authorities. B98 also owns the research-egress/content-isolation portion of this pass.


## 2026-11-24 — structural/platform assurance decision mapping

No new ADR series is created by this pass. The source findings are assigned to existing decisions to avoid duplicate authorities:

| Existing decision | Additional evidence/decision detail | Status |
|---|---|---|
| B77 / B89 | The 18-plane gate checks enum coverage, non-empty descriptive fields and implementation-path existence only; freeze requires source/callsite/integration/trust/enforcement/test/deployment evidence | OPEN |
| B70 | Audit hash chain and HMAC checkpoint need durable event custody, external checkpoint retention, trusted time and incident lifecycle | OPEN |
| B72 / B78 | Release/self-improvement admission requires independent signer/reviewer, SBOM/build provenance, staged approval and rollback | OPEN |
| B82 / B102 | Platform enrollment, signed grants, issuer/device binding, session revocation and remote policy freshness | OPEN |
| B81 / B103 | Encrypted memory must add tenant/principal/purpose/consent/retention/tombstones and durable replica semantics | OPEN |
| B99 | Agent skill registration must be separated from independently qualified domain competence and action authority | OPEN |
| B104 | Mobile/offline replay and dispatch records need durable idempotency and indeterminate-effect reconciliation | OPEN |

The gate and cryptographic adapters remain useful primitives. No architecture freeze or production assurance is inferred from their existence.


## 2026-11-24 — agent/evidence/MIRROR WORLD/global-impact decision mapping

No new ADR series is created. Reconcile this pass with existing open decisions:

| Existing ADR | Additional detail to include | Status |
|---|---|---|
| B79/B80/B85 | One canonical dispatch lifecycle and typed intent/request/task/step/execution/attempt/dispatch identifiers | OPEN |
| B86/B87 | Full DAG coverage, leases, cancellation, retries, idempotency and uncertain side-effect states | OPEN |
| B88 | Consensus independence across model/provider/data/team/failure domain; disagreement and correlated error semantics | OPEN |
| B90/B97 | Structural output verification separated from semantic claim-source evidence and lineage | OPEN |
| B91 | Campaign manifest, holdout custody, immutable execution evidence, evaluator identity and independent approval | OPEN |
| B92 | FINCH target/horizon, leakage-safe temporal validation, calibration, proper scoring and drift | OPEN |
| B93/B100 | MIRROR WORLD model manifest, calibration, validation, uncertainty/OOD envelope and non-actuating Reality Bridge | OPEN |
| B81/B103 | Global memory payload custody, replica health, consistency, consent, deletion and anti-rollback | OPEN |
| B82/B102 | Canonical issuer, tenant, session/device scope, freshness and revocation authority for agent dispatch | OPEN |
| B83/B84/B101 | Segregated project funds, ledger, contributor safeguards, baseline/counterfactual and independent impact outcome | OPEN |
| B95/B96/B98 | Provider/source identity, research egress, signed receipts and untrusted-content isolation | OPEN |

Where these details overlap an earlier ADR, consolidate the existing decision text rather than creating duplicate authority. All W01–W12 remain PARTIAL.


## 2026-11-24 — tool/provider/protocol/effect decision mapping

No new ADR series is created. Reconcile the findings with existing open decisions:

| Existing ADR | Additional detail to include | Status |
|---|---|---|
| B70 | Durable trace/audit event envelope, external head custody, trusted time and incident workflow | OPEN |
| B71/B96/B98 | DNS resolution/pinning, socket-level egress, provider attestation and untrusted response isolation | OPEN |
| B72 | Signed tool/provider artifact, build digest, capability manifest and release lifecycle | OPEN |
| B79/B102 | Authenticated principal/tenant/session/device and policy epoch bound to exact tool action | OPEN |
| B80/B85/B86 | Durable operation/attempt IDs, idempotency, provider effect certainty, receipt and compensation | OPEN |
| B90/B97 | Tool input/output provenance, source authenticity and claim-to-evidence lineage | OPEN |
| B95 | Provider qualification, residency, schema/capability compatibility and adapter contract | OPEN |
| B104 | Offline/provider unified durable intent and indeterminate side-effect reconciliation | OPEN |

Where these requirements overlap existing decisions, consolidate rather than create parallel authorities. W01–W12 remain PARTIAL.


## 2026-11-24 — memory, crypto, multimodal and placement decision mapping

Consolidate these requirements into existing open ADRs; do not create duplicate authorities:

| Existing ADR | Additional detail to include | Status |
|---|---|---|
| B70/B77 | Durable memory/audit deletion evidence, external checkpoints and evidence-backed release state | OPEN |
| B72 | SBOM, reproducible/independent build provenance, signer roles and staged release approval | OPEN |
| B73/B74 | Offline trust freshness, durable media/memory sync and conflict/deletion propagation | OPEN |
| B76/B99 | Agent specialist qualification, domain scope, expiry and independent reviewer evidence | OPEN |
| B81/B103 | Canonical memory envelope, execution-scoped hydration, typed degraded context, retention/tombstones and replica consistency | OPEN |
| B82/B102 | KMS/HSM-backed key authority, trust-root rotation, attestation freshness and distributed revocation | OPEN |
| B85/B87 | Agent admission, lease, health/capacity and deterministic resource placement | OPEN |
| B90/B94/B97 | Multimodal source custody, derivative lineage and evidence-to-claim provenance | OPEN |
| B92/B93/B100 | Media/model/snapshot binding, calibrated domain validity and MIRROR WORLD replay | OPEN |
| B95 | Durable global storage/provider adapters and data residency contract | OPEN |
| B101 | Resource cost/energy/carbon accounting and independently measured community outcomes | OPEN |
| B104 | Durable offline memory/media outbox, tombstones and indeterminate delivery reconciliation | OPEN |

Where a requirement crosses multiple ADRs, define one authoritative owner and reference the shared contract rather than duplicating it. W01–W12 remain PARTIAL.


## Branching cognition, FRL, reverse engineering and domain operations — 2026-11-24

| Existing ADR mapping | Consolidated decision question | Status |
|---|---|---|
| B75/B90/B97 | Distinguish structural, source-checked, empirical, formal-proof and operational evidence; define claim lineage and no silent promotion | OPEN |
| B78/B91 | Bind campaign manifest, evaluator identity, executed cases, holdout custody, per-case results and independent admission | OPEN |
| B85/B87 | Define bounded hypothesis-branch DAG, branch budget, lease/cancel/prune/merge and fair scheduling without implying concurrent execution prematurely | OPEN |
| B88 | Define independence groups and correlated failure across models, providers, sources, tools, datasets and verifiers | OPEN |
| B93/B100 | Bind domain model validity, calibration, uncertainty/OOD and non-actuating Reality Bridge | OPEN |
| B96/B98 | Define authorized RE acquisition, parser isolation, target scope, safe egress and untrusted-content handling | OPEN |
| B99 | Require specialist qualification, jurisdiction, calibration, validity/expiry, conflict disclosure and escalation | OPEN |
| B101 | Separate activity/output from net environmental/community outcome; baseline, counterfactual, safeguards and independent verification | OPEN |
| B102/B104 | Bind terminal and RE operations to issuer/session/device, durable intent, receipts and uncertain-effect reconciliation | OPEN |

No new ADR identifiers are created in this pass. Existing proposals remain OPEN until separately reviewed and accepted. W01–W12 remain PARTIAL.


## 2026-11-24 — cognitive branching, formal evidence, MIRROR WORLD and systems understanding reconciliation

Consolidate this pass into existing decision authorities; do not create a duplicate ADR series:

| Existing ADR | Reconciliation detail | Status |
|---|---|---|
| B79/B80/B85/B87 | Hypothesis/branch, plan, step, execution and operation identity; DAG coverage, concurrency, cancellation and lease semantics | OPEN |
| B86/B104 | Retry/idempotency and uncertain side-effect reconciliation across terminal, tools and provider operations | OPEN |
| B88/B90/B97 | Evidence independence, claim classes, source anchoring and semantic admission | OPEN |
| B91 | Evaluation campaign execution, holdout custody, leakage prevention and evaluator identity | OPEN |
| B92/B93/B100 | Forecast/model calibration, uncertainty/OOD, validity and Reality Bridge | OPEN |
| B94/B97 | Multimodal custody, derivative lineage, consent and source anchoring | OPEN |
| B76/B99 | Specialist qualification, scope, jurisdiction, expiry and independent review | OPEN |
| B71/B96/B98 | Authorized acquisition, safe egress, content isolation and provider/source identity | OPEN |
| B72/B77/B89 | Signed model/kernel/artifact manifests, build provenance and evidence-backed freeze | OPEN |
| B81/B103 | Durable branch/evidence/experiment state, tenant isolation, retention and deletion | OPEN |
| B83/B84/B101 | Restricted funds, double-entry accounting, safeguards and independently verified environmental outcomes | OPEN |
| B95 | Production placement/provider adapters, residency, capacity, energy/cost and failure-domain contracts | OPEN |

No ADR is closed by this documentation pass. W01–W12 remain PARTIAL.


## 2026-11-24 — execution semantics, agent scheduling, provider effects and distributed fabric reconciliation

Consolidate into existing decision authorities; do not create duplicate ADRs:

| Existing ADR | Reconciliation detail | Status |
|---|---|---|
| B79/B80/B85/B87 | Caller-bound execution identity, branch/plan/step/attempt IDs, full DAG admission and lease semantics | OPEN |
| B86/B104 | Provider/tool/offline idempotency, effect certainty, durable receipts and reconciliation | OPEN |
| B88/B90/B97 | Consensus independence, evidence lineage and semantic result admission | OPEN |
| B81/B103 | Durable memory payload custody, tenant isolation, tombstones and verified replicas | OPEN |
| B82/B102 | Principal/session/device/workload authority continuity | OPEN |
| B71/B96/B98 | DNS/socket egress enforcement and provider/source attestation | OPEN |
| B72/B77/B89 | Artifact/model signing lifecycle, external checkpoint and evidence-backed freeze | OPEN |
| B91 | Evaluation campaign execution and independent holdout custody | OPEN |
| B94 | Multimodal custody, transformation lineage, consent and retention | OPEN |
| B95 | Placement telemetry freshness, reservation/lease and production adapters | OPEN |
| B76/B99 | Specialist qualification as scheduling eligibility | OPEN |
| B83/B84/B101 | Financial custody, governance and independent outcome evidence | OPEN |

No ADR is closed by this documentation pass. W01–W12 remain PARTIAL.


## 2026-11-24 — domain calibration, specialist qualification, cyber-range assurance and public-impact accounting

| Existing ADR | Reconciliation detail | Status |
|---|---|---|
| B76/B99 | Specialist competence, jurisdiction, conflict, expiry and suspension must be scheduler-verifiable | OPEN |
| B88/B90/B97 | Source-anchored claims, evidence independence groups and semantic admission | OPEN |
| B91 | Evaluation campaign exact-artifact binding, holdout custody and independent assessors | OPEN |
| B92/B93/B100 | FINCH/MIRROR WORLD target definition, temporal calibration, drift and model validity | OPEN |
| B94 | Observation/media/cyber artifact custody and transformation lineage | OPEN |
| B71/B96/B98 | Cyber authorization manifest and acquisition enforcement boundaries | OPEN |
| B83/B84/B101 | Funds segregation, double-entry accounting, community governance and independently verified impact | OPEN |

No new ADRs created; reconcile any B105/B106 references into canonical existing decisions only after owner/source review. W01–W12 remain PARTIAL.

## Cross-workstream synthesis disposition — 2026-11-25

The [Cross-Workstream Dependency and Canonical Ownership Reconciliation](NORYX7_CROSS_WORKSTREAM_DEPENDENCY_AND_CANONICAL_OWNERSHIP_RECONCILIATION.md) consolidates the dependency graph and responsibility boundaries without creating duplicate ADRs. Existing blocking decisions ADR-B01–B08 remain open until source-level ownership and call-path evidence is collected. Existing high-priority decisions H01–H12 remain governed by this backlog. The synthesis does not decide unresolved implementation ownership by assertion and does not authorize integration, testing, merge or deployment. W01–W12 remain PARTIAL.


## 2026-11-25 — ingress/effect/release reconciliation

Existing ADR-B56–B62 remain OPEN and are clarified by [Ingress, External Effects, Release Evidence and Cross-Workstream Closure Reconciliation](NORYX7_INGRESS_EFFECTS_RELEASE_AND_CLOSURE_EVIDENCE_RECONCILIATION.md):
- B56: canonical effect/receipt/compensation outcome state machine.
- B57: separate topological ordering, concurrency admission, resource reservation and dispatch.
- B58: distinguish digest integrity, keyed authentication, signer identity and model/provider provenance.
- B59: reconcile actual provider usage/cost/latency from receipts; static metadata is not metering truth.
- B60: reconcile route-level authentication and principal provenance across gateway and direct API paths.
- B61: per-platform artifact build, test, sign, promotion and rollback evidence.
- B62: machine-readable audit evidence scope, exclusions, revision and limitations.

No new ADR IDs are created and no decision is closed by documentation alone. W01–W12 remain PARTIAL.
