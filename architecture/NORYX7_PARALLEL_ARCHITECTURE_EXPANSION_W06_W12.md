# NORYX7 — Parallel Architecture Expansion W06–W12

**Status:** source-reconciled design proposal; not frozen  
**Date:** 2026-11-22  
**Source revision:** `main` at the inspected source snapshot; individual anchors are listed below  
**Scope:** architecture and contracts only. No runtime implementation, integration, tests, merge or deployment.

## 1. Purpose and evidence discipline

This document advances W06–W12 together. It reconciles observed source behavior with the architecture that must govern it. A source component is evidence that a bounded mechanism exists; it is not proof of production deployment, operational completeness, correctness under all conditions, or system-wide authority.

Every claim is classified as:
- **Observed:** directly visible in the inspected source.
- **Proposed:** normative architecture to be adopted after cross-stream decisions.
- **Open:** evidence or decision still missing.
- **Excluded:** explicitly outside the current architecture-freeze scope.

The canonical plane count remains 18. These workstreams add contracts and sub-systems, not new canonical planes.

## 2. W06 — NEXUS semantics, evidence and formal reasoning

### 2.1 Source reconciliation

Observed source anchors:
- `core/universal_intelligence.py`: `Evidence`, `DomainAssessment`, `SpecialistRoute`, `FabricResult`, deterministic keyword/risk routing, evidence-strength averaging, contradiction and uncertainty checks.
- `core/contracts.py`, `core/context.py`, `core/memory.py`: typed task/result/context and memory structures (exact canonical cross-package equivalence remains open).
- `core/verification.py`: task/result/state checks; current output verification is largely presence/shape-oriented and does not establish semantic truth.
- `core/subtask_verification.py`, `core/metacognitive_challenge.py`: verification/challenge surfaces; not by themselves a general proof kernel.
- `ecosystem/boundaries.py`: `IntentEnvelope` carries front, operation, payload digest and principal; it is a cross-front intent boundary, not a complete semantic IR.
- `ecosystem/global_fabric.py`: memory record digests, versions, replica identifiers and identity-authorization index; in-memory only.
- `services/jarvis-runtime-rs/src/lib.rs`: canonical JSON digest helper; not evidence of cross-language semantic equivalence.
- `services/jarvis-gateway-go/main.go`: digest endpoint; not a canonical authenticated wire implementation.

### 2.2 Normative semantic stack

NEXUS is split into independently versioned layers:
1. **NEXUS-IR:** typed, language-neutral semantic graph. Nodes represent entities, claims, actions, constraints, observations, decisions and relations. Every node has stable ID, type URI, schema version, tenant/data scope, provenance references and lifecycle state.
2. **NEXUS-Wire:** transport envelope carrying message ID, correlation ID, execution ID, sender principal/workload/device, audience, issued/expiry times, nonce, schema/profile IDs, payload digest, provenance digest, signature/attestation references and delivery semantics.
3. **NEXUS-Surface:** UI/API-specific projection. It may omit or transform presentation fields but cannot mint identity, authority, evidence validity or execution status.
4. **NEXUS-Ontology Registry:** governed vocabularies, aliases, domain schemas, deprecation and migration metadata.
5. **NEXUS-Canonicalization Profile:** deterministic serialization and digest rules, including Unicode normalization, numeric representation, ordering, null/omission policy, timestamp precision and unknown-field behavior.

No implementation language is the semantic authority. Python, Go, Rust, Kotlin, Swift and TypeScript adapters must map to the same normative schema/profile versions. A digest match proves byte/canonical-form agreement only; it does not prove semantic equivalence or truth.

### 2.3 Evidence ontology

Use a non-interchangeable evidence family:
- **SourceRecord:** origin, publisher/author, retrieval time, source version, license/permission, integrity digest and acquisition method.
- **Observation:** directly observed measurement/event, instrument, calibration, sampling window, uncertainty and chain of custody.
- **Claim:** proposition, scope, quantifiers, temporal validity, jurisdiction/domain and claim status.
- **Inference:** derivation graph, premises, rules/model version, assumptions and uncertainty propagation.
- **FormalProof:** proposition/theory encoding, proof object, checker identity/version, trusted kernel, axioms and verification result.
- **EmpiricalResult:** protocol, dataset, equipment, controls, sample, statistical method and replication status.
- **SimulationResult:** world/scenario manifest, simulator build, parameters, calibration, random seed, model discrepancy and holdout status.
- **ExpertReview:** reviewer qualification/role, conflict-of-interest disclosure, scope, timestamp and signed disposition.
- **DecisionRecord:** decision owner, policy version, accepted evidence set, dissent, expiry/review trigger and appeal path.

Evidence states: `unreviewed → structurally_valid → source_checked → independently_checked → accepted_for_scope`; alternate terminal states are `rejected`, `contested`, `expired`, `withdrawn`, `quarantined`. State is scoped: acceptance for one domain, jurisdiction, time interval or risk class does not imply universal acceptance.

A confidence score is not proof. An evidence-strength average is not a calibrated probability unless its calibration model, independence assumptions and domain validity are established. Contradiction must remain explicit; aggregation cannot erase dissent or convert missing evidence into negative evidence.

### 2.4 FRL / formal reasoning boundary

FRL proof admission requires:
- exact proposition and formal language/version;
- theory/axiom set and dependency digests;
- proof artifact digest;
- checker and trusted-kernel identity/version;
- resource/time limits and termination status;
- independent replay or checker diversity where risk warrants;
- explicit result: `proved`, `disproved`, `unknown`, `timeout`, `unsupported`, `checker_error`.

Empirical and simulation evidence must never be promoted to formal proof. A failed proof attempt is not a counterexample unless the counterexample itself is validated. Gödel/incompleteness-related limitations are scoped to formal systems and propositions; they do not justify declaring arbitrary empirical claims undecidable.

### 2.5 W06 open decisions

- Canonical schema owner and release governance across languages.
- Evidence identity, source acquisition, retention, rights and deletion.
- Trust model for checkers, model-assisted proof construction and independent verification.
- Ontology extension permissions and conflict resolution.
- Semantic-equivalence criteria beyond digest equality.
- Linkage to ADR-B05, ADR-B07, ADR-H01–H03 and ADR-H11.

## 3. W07 — MIRROR WORLD, simulation and Reality Bridge

### 3.1 Source reconciliation

Observed:
- `core/cyber_range.py`: synthetic targets constrained to sandbox trust zone, owner authorization, bounded symbolic attack phases; no real target/network execution path in this module.
- `core/sandbox.py`: fail-closed state machine with network, host mutation, core access and real-secret controls; privileged profile flags rejected.
- `core/evaluation_campaign.py`: deterministic generated cases, holdout selection and evaluation matrix recording; it does not itself infer truth from recorded evidence.
- `core/adversarial.py`: deterministic synthetic scenario generation, bounded to one million scenarios; no external attack execution.
- `ecosystem/global_scale.py`: synthetic scenario grid, capacity/region/cell abstractions, bounded in-memory event queue, metrics and staged self-healing state.
- `core/execution_fabric.py`: environment adapter boundary; its existence does not establish a calibrated digital twin or safe simulation-to-real transition.

### 3.2 World model architecture

MIRROR WORLD is a family of isolated, versioned world models, not one universal simulator:
- **World Registry:** world ID, domain, owner, source dataset lineage, spatial/temporal reference frame, schema version, trust zone and lifecycle.
- **Entity/Relationship Graph:** typed entities, state, relations, constraints, provenance and temporal validity.
- **Scenario Manifest:** objective, initial state, assumptions, interventions, actors, boundary conditions, seed, parameter ranges, stop conditions and expected observations.
- **Model Registry:** simulator/model build, dependencies, training/calibration datasets, known limitations, validity envelope and approval state.
- **Experiment Runner:** deterministic orchestration, resource budget, isolation profile, event journal and reproducibility manifest.
- **Observation/Outcome Store:** raw outputs, derived metrics, uncertainty, anomalies, provenance and checker disposition.
- **Calibration Registry:** measured reference data, error bounds, calibration date, drift triggers and independent review.
- **Holdout Governance:** immutable holdout identity, separation from tuning, leakage controls and disclosure rules.

World families are separately typed: software/cyber, network/infrastructure, physical/industrial, environmental/ecological, biological/medical, economic/market, logistics/agriculture, and social/policy. A common graph schema does not imply shared physical validity.

### 3.3 Fidelity and uncertainty

Every model declares fidelity dimensions rather than one opaque score:
- structural completeness;
- parameter calibration;
- temporal resolution;
- spatial resolution;
- causal coverage;
- stochastic representation;
- boundary-condition coverage;
- external validation;
- known model discrepancy;
- operational validity window.

Simulation output must include uncertainty and assumptions. A high-fidelity label is prohibited without evidence and a domain-specific acceptance rule. Model drift or out-of-envelope inputs move the result to `degraded` or `unsupported`, not silently to a valid state.

### 3.4 Reality Bridge

The default is **simulation-only**. A simulation result cannot directly invoke a real-world action. A separate Reality Bridge proposal must pass:
1. asset/target ownership and explicit scope authorization;
2. independent real-world identity and capability evaluation;
3. policy and jurisdiction checks;
4. safety case with hazards, reversibility, impact and containment;
5. human approval for consequential or irreversible actions;
6. fresh authorization at dispatch, with bounded expiry and one-use execution identity;
7. pre-dispatch durable reservation and idempotency policy;
8. execution adapter constrained to the approved target/action set;
9. post-action observation, verification and audit;
10. abort/rollback/compensation plan where physically possible.

No simulation credentials, identities, network routes, secrets or capabilities cross into production. A one-way export of sanitized recommendations is the default bridge. Any live actuation remains a separately authorized future capability.

### 3.5 W07 open decisions

- World graph ontology and cross-domain identity.
- Model registry, calibration and holdout custodians.
- Safe execution isolation, network egress and artifact custody.
- Reality Bridge policy owner and permitted action taxonomy.
- Reproducibility requirements for nondeterministic models.
- Linkage to ADR-H04/H05 and ADR-B05/B08.

## 4. W08 — surfaces, distribution and offline continuity

### 4.1 Observed surface distinctions

- Python gateway exposes health, session creation and execution; it relies on bootstrap token and HMAC signing secret and uses client ID as session identity.
- Gateway documentation states TLS must terminate in production; the source itself does not establish TLS termination, multi-instance shared revocation or client-ID-to-verified-principal mapping.
- Android Browser is a standalone WebView surface with HTTPS navigation policy and gateway session client. Bootstrap secret provisioning and device-bound trust remain open.
- iOS adapter has local device/capability/epoch/replay abstractions; signed remote grants, durable replay and remote revocation are not established by that abstraction.
- Android audio bridge exposes a PCM callback boundary; concrete permission, capture and retention controls belong to the platform integration.
- TypeScript interaction is a presentation surface, not a policy authority.
- Go and Rust services are separate artifacts; their existence does not establish feature parity or a shared deployment lifecycle.

### 4.2 Surface contract

Every surface is a non-authoritative client. It can:
- capture consented user intent;
- display policy decisions and execution status;
- hold short-lived, audience-bound presentation/session state;
- request an operation using a versioned envelope;
- receive an explicit accepted/rejected/indeterminate result.

It cannot mint principal identity, expand capability, override policy, attest its own trust, commit canonical state or reinterpret a failed/unknown result as success.

Surface-specific manifests define: platform, app/package identity, build/release digest, device binding, permission inventory, local storage, secret class, session lifetime, network policy, offline behavior, data capture, accessibility and decommission behavior.

### 4.3 Offline contract

Offline mode is a separately governed trust mode:
- signed cached policy and schema snapshots carry issuer, version, digest, validity window and monotonic epoch;
- action classes are partitioned into allowed-local, queue-only, online-required and always-denied;
- high-impact operations require fresh online revocation and authority state;
- offline queues carry idempotency key, causal context, expiry, original authorization reference and provenance;
- synchronization performs conflict classification, not last-write-wins for authority or security state;
- revocation staleness beyond the configured limit disables affected actions;
- restore must not roll back monotonic security epochs or replay-consumption state.

### 4.4 W08 open decisions

Credential enrollment/rotation, client-to-principal mapping, mobile secure storage, WebView threat model, offline revocation freshness, durable outbox, cross-device conflict semantics and surface artifact signing.

## 5. W09 — security, assurance and supply chain

Security is a composition of independent controls, not a single boolean:
- identity proves who/what a principal is;
- authentication proves possession/control of an authenticator;
- authorization binds principal, action, resource, context and expiry;
- policy decides permitted action under risk and jurisdiction;
- capability constrains what a component can attempt;
- ActionGate enforces the final dispatch decision;
- egress constrains reachable destinations;
- execution adapter constrains the actual effect;
- attestation records the state and provenance of the operation;
- audit preserves an independently reviewable record.

The source anchors include `core/verification.py`, `core/cyber_range.py`, `core/sandbox.py`, `core/egress.py`, `core/secure_boot.py`, `core/supply_chain.py`, `core/key_lifecycle.py`, `core/trust_chain.py`, `core/control_plane.py` and gateway authentication. No one module alone establishes the complete chain.

Required architecture objects:
- threat model and trust-zone graph;
- principal/workload/device taxonomy and issuer registry;
- key hierarchy, custody provider, rotation, revocation and recovery;
- signed build provenance and artifact manifest;
- dependency/SBOM and vulnerability disposition;
- release approval, staged rollout and rollback authority;
- security event taxonomy and immutable audit;
- incident command, containment and evidence preservation;
- independent recovery root and break-glass dual control.

Cryptographic agility is mandatory: algorithm identifiers, key IDs, versioned envelopes, migration overlap, downgrade prevention and emergency revocation must be explicit. Post-quantum transition planning is a separate cryptographic lifecycle decision; it does not follow from mathematical-intelligence capabilities or the Riemann hypothesis.

## 6. W10 — domain operational fabrics

### 6.1 Current source coverage

`core/universal_intelligence.py` currently names software engineering, architecture engineering, legal intelligence, medical evidence, scientific research, finance/economics and general reasoning as deterministic routing domains. This is a bounded routing vocabulary, not proof of domain specialist agents, professional validation or complete domain packages.

The system-wide domain catalog may include:
- software, systems and cybersecurity;
- engineering, infrastructure and manufacturing;
- science and research;
- medicine and public health;
- law, regulation and public administration;
- finance, economics and accounting;
- environment, climate and ecology;
- agriculture, food systems and logistics;
- education and learning;
- energy and utilities;
- construction, mobility and transport;
- social services and community operations;
- media, information integrity and journalism.

### 6.2 Required Domain Manifest

Each domain package must declare:
- domain ID, version, owner and jurisdiction;
- supported task classes and prohibited task classes;
- authoritative source classes and source hierarchy;
- evidence requirements and validity windows;
- domain ontology and unit/measurement standards;
- model/specialist qualifications and conflict disclosures;
- uncertainty, harm and risk taxonomy;
- mandatory human-review triggers;
- escalation contacts/roles and emergency stop;
- data minimization, retention and residency;
- permitted tools, external services and physical interfaces;
- outcome acceptance and appeal process;
- known limitations, update cadence and deprecation plan.

### 6.3 Domain validity and human authority

A domain result is valid only within its declared scope. Medical output is not a diagnosis or treatment authorization; legal analysis is not legal representation; financial analysis is not a regulated investment instruction; engineering recommendations do not authorize physical actuation. High-consequence decisions require appropriately qualified human review and applicable local law.

Domain packages may contribute evidence and recommendations. They cannot grant their own execution authority or weaken global security policy. Domain-specific rules can be stricter than global policy, never weaker.

## 7. W11 — performance, operations and release lifecycle

### 7.1 Source reconciliation

Observed:
- `ecosystem/global_scale.py` defines in-memory region/cell registries, capacity selection, work queues, resource budgets, degradation modes, bounded metric samples, DR target selection and staged self-healing state.
- These are control-plane models and in-memory accounting primitives; they are not cloud infrastructure, durable queues, fleet telemetry or measured SLOs.
- `gateway/server.py` is an HTTP boundary with a 16 KiB request-body limit, no-store response header and generic runtime-failure response; production TLS is explicitly external.
- `render.yaml` defines a Python service only; it does not describe the release lifecycle for Go, Rust, Android, iOS or Browser artifacts.
- Seven CI workflow definitions were previously inventoried; their presence does not establish production promotion, release signing, rollback or disaster recovery.

### 7.2 Operational architecture

Separate planes:
1. **Build plane:** source revision, reproducible build, dependency lock, SBOM, provenance and signed artifact.
2. **Release plane:** approval, environment promotion, canary, rollout, rollback and decommission.
3. **Control plane:** desired state, configuration, policy distribution, topology and fleet inventory.
4. **Execution plane:** workloads, adapters, queues and resource allocation.
5. **Observability plane:** metrics, traces, structured events and audit; telemetry must not become a covert content store.
6. **Reliability plane:** health/readiness/liveness, backpressure, circuit breaking, rate limits, capacity reserve, DR and restore.
7. **Incident plane:** severity, ownership, containment, evidence preservation, communication and post-incident review.

### 7.3 Required service objectives

Define per workload class, not one global uptime number:
- availability and successful completion;
- latency percentiles and deadline misses;
- queue age/depth and backpressure;
- resource utilization and budget overruns;
- authorization rejection and policy-denial rates;
- verification failure and indeterminate-result rates;
- data durability, recovery point and recovery time;
- replication lag, revocation propagation and offline staleness;
- cost per accepted task and fairness across tenants;
- privacy/security incidents and audit completeness.

Each SLO requires measurement source, population, window, exclusion policy, owner, alert threshold, error budget and response runbook. No target is asserted until workloads and deployment topology are known.

### 7.4 Release and deployment contract

One release manifest references each independently deployable artifact: Python gateway/runtime, Go service, Rust runtime, Android Browser/bridge, iOS adapter, UI assets and model/provider configuration. It binds artifact digest, source commit, build provenance, schema compatibility, configuration version, key references, environment, approval, rollout cohort and rollback target.

Secrets are injected from an identified secret manager or platform keystore; never stored in source, image, browser bundle or ordinary configuration. Production and staging have distinct trust roots. Rollback must not roll back security epochs, revocations, audit sequence or consumed authorization IDs.

### 7.5 W11 open decisions

Production topology and source of truth, CI workflow ownership, artifact signing and provenance, secret manager, environment promotion, telemetry retention, SLO targets, capacity/fairness policy, durable queues, backup/restore and incident command.

## 8. W12 — product, marketplace, finance and community ecosystem

### 8.1 Boundary principle

Product/economic subsystems are separate from execution authority and from the security audit chain. They may request actions but cannot authorize tools, change policy, elevate agents or bypass ActionGate.

Distinct ledgers and bounded responsibilities:
- **Usage ledger:** metering, quota and billing evidence.
- **Payment ledger:** payment processor references, settlement, refunds and disputes.
- **Internal contribution ledger:** time, materials, verified work, credits and community allocations.
- **Marketplace registry:** offers, provider identity, catalog, terms, availability and fulfillment state.
- **Governance record:** proposals, voting eligibility, decisions, conflict disclosures and appeal.
- **Impact ledger:** environmental/social outcomes, methodology, evidence and independent review.
- **Security audit:** authorization, dispatch, state transitions and incident evidence; inaccessible to commercial mutation.

No financial balance is inferred from an execution receipt, no contribution credit is treated as legal tender without an explicit legal model, and no payment event proves service quality or environmental impact.

### 8.2 Required product/tenant architecture

- tenant and organization identity, membership, role and separation;
- onboarding/KYC or legal checks only where required by jurisdiction and product;
- catalog/provider onboarding and verification;
- pricing, subscription, metering, usage caps and transparent fees;
- payment authorization, settlement, refund, chargeback and reconciliation;
- tax/invoicing and consumer protection obligations;
- data portability, account closure and retention;
- dispute resolution, abuse reporting and independent appeals;
- community contribution verification, safety, insurance and safeguarding;
- governance quorum, conflicts, minority rights and emergency authority;
- impact measurement, anti-double-counting and independent audit.

### 8.3 Community and environmental work

For community projects, distinguish pledged funds, received funds, restricted funds, allocated budget, committed expenditure and verified impact. Each project has owner, location, permits, risk assessment, safeguarding, procurement rules, contributor consent, insurance, safety training, evidence of completion and public reporting. Volunteer time and paid work must be legally distinguished.

Environmental claims require baseline, methodology, boundary, measurement interval, uncertainty, additionality, permanence and leakage analysis. Cleanup/recycling/reforestation counts must not be converted to carbon credits or health outcomes without the applicable independent standard and verification.

### 8.4 W12 open decisions

Legal entity and jurisdiction, tenant model, payment providers and safeguarding, internal-credit legal status, governance constitution, dispute/appeal authority, impact standards, insurance and project procurement.

## 9. Cross-workstream contract dependencies

| Shared contract | Primary owner stream | Consumers | Freeze dependency |
|---|---|---|---|
| Principal / workload / device taxonomy | W01 | W02–W12 | B0 |
| Runtime lifecycle and dispatch boundary | W02 | W03–W12 | B0 |
| State journal, idempotency and recovery | W03 | W04, W07–W12 | B0 |
| Agent delegation and result admission | W04 | W05–W10 | B0 |
| Provider route / agent route / placement / scheduler | W05 | W02, W04, W08, W11 | B1 |
| NEXUS-IR, Wire, provenance and evidence states | W06 | W02–W12 | B0/B1 |
| World/scenario manifest and Reality Bridge | W07 | W05, W06, W09, W10 | B1 |
| Surface identity/session/offline envelope | W08 | W01–W03, W09, W11 | B0/B1 |
| Trust zones, key custody and supply chain | W09 | All | B0 |
| Domain manifest and escalation | W10 | W06–W09, W12 | B1 |
| SLO, release and incident contracts | W11 | W02–W09, W12 | B1 |
| Tenant, finance, governance and impact ledgers | W12 | W01, W06, W09–W11 | B1/B2 |

## 10. Gap taxonomy and disposition

Each source-to-contract mismatch must be assigned one or more labels:
- **MISSING:** no source mechanism or architecture contract found.
- **AMBIGUOUS:** multiple plausible owners or meanings.
- **DUPLICATE:** overlapping mechanisms without precedence.
- **CONFLICTING:** incompatible contracts or invariants.
- **ORPHANED:** component has no caller/owner or no consumer.
- **UNBOUNDED:** resource, scope, retention, retry or authority has no hard bound.
- **UNVERIFIED:** claim lacks independent evidence.
- **STALE:** version/epoch/revocation freshness is insufficient.
- **UNSUPPORTED:** adapter or domain is claimed without actual capability.
- **UNSAFE-FALLBACK:** failure path silently broadens authority or changes semantics.
- **HIDDEN-COUPLING:** lifecycle/state/identity dependency crosses a boundary without contract.
- **GOVERNANCE-GAP:** no accountable owner, approval, appeal or incident authority.

No gap is closed merely by adding a document. Closure requires a named owner, normative contract, source mapping, failure semantics and future acceptance evidence.

## 11. Architecture closure criteria for W06–W12

A workstream may become DECIDED only when:
1. source inventory and caller graph are sufficiently complete for its scope;
2. each contract has one owner and version;
3. inputs, outputs, identity, state, evidence and failure outcomes are defined;
4. dependencies and forbidden couplings are explicit;
5. privacy, jurisdiction, safety and resource bounds are addressed;
6. open gaps are either resolved or explicitly deferred with owner and reason;
7. cross-stream decisions are reconciled with the 18 canonical planes.

FROZEN requires explicit architecture approval and a manifest of accepted ADRs. IMPLEMENTED and VERIFIED remain later, separate states. All W06–W12 are **PARTIAL** at this point.

## 12. Explicit non-goals of this cycle

No code generation, runtime refactor, component linking, schema migration, test execution, benchmark, CI rerun, deployment, release, payment integration, live external target testing or real-world actuation is authorized by this document.
