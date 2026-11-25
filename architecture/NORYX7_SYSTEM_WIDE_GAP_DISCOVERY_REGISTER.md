# NORYX7 — System-wide architecture gap discovery register

**Status:** active discovery baseline; architecture-only; not a completeness claim  
**Parent:** System-wide Architecture Closure / PR #212

## 1. Purpose

The architecture cannot be declared complete merely because every known plane has a document. Discovery must also find capabilities absent from the initial decomposition, overlapping implementations, hidden authority paths, missing lifecycle states and operational conditions that emerge across subsystem boundaries.

The cryptographic inventory is a concrete example: the repository already contains crypto boundaries, envelope encryption, key lifecycle, secure channel, identity, attestation, trust-chain and multi-authorization components. Finding these later means the original architecture map was not sufficiently exhaustive. The response is not to bolt on an isolated crypto feature; it is to repeat discovery systematically across every plane and cross-cutting domain.

This register controls discovery and reconciliation. It does not claim that every listed source has been exhaustively read or that proposed contracts are implemented.

## 2. Independent status axes

**Architecture status:** UNKNOWN, DISCOVERED, MAPPED, CONTRACTED, DECIDED, DEFERRED, FROZEN.

**Implementation/evidence status:** ABSENT, PRESENT, PARTIAL, UNASSESSED, VERIFIED. VERIFIED is permitted only with evidence tied to an exact commit, configuration, environment and acceptance scope.

Never collapse these axes. A present implementation can be architecturally unmapped; a contracted capability can be absent from code; a green test can verify only a narrow behavior.

## 3. Gap taxonomy

| Code | Class | Meaning |
|---|---|---|
| G01 | Missing | Required capability or lifecycle step has no identified owner/design |
| G02 | Ambiguous | Responsibility, term, state or boundary admits multiple interpretations |
| G03 | Duplicate | Multiple components claim the same canonical responsibility |
| G04 | Conflict | Contracts or authorities contradict one another |
| G05 | Orphan | Component, data, API, job or surface has no owning lifecycle |
| G06 | Unbounded | Work, storage, retries, fan-out, cost, time or privilege lacks a hard bound |
| G07 | Unverified | Claim lacks required evidence; not proof that code is defective |
| G08 | Stale | Contract, schema, key, model, policy or artifact can outlive validity |
| G09 | Unsupported | Required environment, mode, failure or interoperability case is not covered |
| G10 | Unsafe fallback | Failure can silently become success, permissive behavior or ambiguous state |
| G11 | Hidden coupling | Dependency on implicit call path, global state or undocumented ordering |
| G12 | Governance gap | Approval, accountability, ownership, retention or escalation is undefined |

## 4. Twelve parallel workstreams — discovery obligations

| Stream | Domain | Required discovery beyond current ADRs | Main gap classes |
|---|---|---|---|
| W01 | Identity, trust and authority | Human, service, agent, device, workload and tenant principals; enrollment, binding, delegation, consent, policy epochs, revocation, emergency authority, break-glass and trust-root recovery | G01–G05, G08, G10, G12 |
| W02 | Runtime topology | Every process entrypoint, coordinator, engine, facade, worker, plugin host, JARVIS lifecycle, startup/shutdown, upgrade and compatibility path | G02–G05, G11 |
| W03 | State, data and recovery | All stores, journals, caches, checkpoints, event streams, snapshots, replicas, migrations, retention, erasure, restore and uncertain external side effects | G01–G06, G08–G10 |
| W04 | Agent fabric | Every agent type and invocation path, capability manifest, trust binding, lease, delegation, supervision, collaboration, cancellation and result admission | G02–G06, G10–G11 |
| W05 | Routing and resources | Provider/model choice, agent allocation, task scheduling, placement, dispatch, quotas, reservations, fairness, backpressure and cost accounting | G02, G04, G06, G11 |
| W06 | Semantics, knowledge and evidence | NEXUS schemas, ontology, canonicalization, source lineage, claims, uncertainty, contradiction, temporal validity, formal proof and scientific evidence | G01–G04, G07–G09 |
| W07 | MIRROR WORLD | Synthetic web, cyber range, software models, digital twins, physical/environmental/economic worlds, simulation fidelity, experiment isolation and Reality Bridge | G01–G04, G06–G10 |
| W08 | Surfaces and distribution | Browser, voice, multimodal, terminal, mobile, desktop, API, edge/cloud/offline, session handoff, local authority and synchronization | G02–G06, G08–G11 |
| W09 | Security and assurance | Cryptographic boundaries, key custody, secure boot, attestation, channel security, authorization replay, audit, threat model, incident response and supply chain | G01–G10, G12 |
| W10 | Domain fabrics | Health, law, finance, science, engineering, agriculture, ecology, climate, education, logistics and public-interest/community domains | G01–G04, G07–G09, G12 |
| W11 | Performance and operations | SLOs, capacity, telemetry, quotas, queueing, overload, degradation, fairness, cost, deployment, upgrades, incident and disaster recovery | G01–G06, G08–G10 |
| W12 | Product and ecosystem | Tenant lifecycle, marketplace, integrations, financial rails, billing, metering, community projects, contributor identity, governance and dispute handling | G01–G05, G08–G12 |

All streams progress concurrently. Dependencies constrain contract acceptance, not discovery: a stream may record a dependency before its upstream decision is frozen.

## 5. Cross-cutting capability checklist

Search for these across all planes, not only in modules whose names suggest them:

1. Identity, authentication, authorization, delegation, consent and revocation.
2. Cryptography, key custody, key rotation, algorithm agility, secure boot, attestation and trust recovery.
3. Data classification, privacy, tenant isolation, retention, deletion, export, residency and replica reconciliation.
4. Provenance, evidence, epistemic state, source independence, temporal validity and audit integrity.
5. Formal methods, proof checking, theorem/counterexample handling, scientific validation and model fidelity.
6. Multimodal ingestion, transformation, alignment, spatial/time coordinates and original-artifact preservation.
7. Human oversight, approvals, emergency stop, appeal, accountability and operator separation.
8. Supply-chain integrity for source, dependencies, builds, models, datasets, plugins and update channels.
9. Scheduling, quotas, budgets, metering, fairness, overload, backpressure and graceful degradation.
10. Federation, discovery, interoperability, protocol/schema negotiation, offline operation and conflict resolution.
11. Observability, audit, alerting, incident response, forensics, backup, restore and disaster recovery.
12. Self-improvement, configuration/policy evolution, staged rollout, rollback and immutable trust roots.
13. Product lifecycle: onboarding, setup, account recovery, support, billing, portability, deletion and exit.
14. Domain validity: jurisdiction, standards, units, uncertainty, expert review and prohibited inferences.
15. Physical-world safety: device capabilities, actuator bounds, fail-safe states, environmental conditions and human override.
16. Accessibility, localization, usability, user comprehension and consent UX.

## 6. Mandatory questions for every component

For every source file, service, API, agent, tool, store, job, surface, model or domain package, record:

- What need does it serve, and what is out of scope?
- Is it code, configuration, schema, documentation, fixture, adapter or external dependency?
- Who owns its lifecycle? Which plane is primary and which are secondary?
- Who may invoke it, under what identity, scope, consent and capability?
- What are its inputs, outputs, side effects and canonical identifiers?
- Which schemas, versions, units, canonicalization rules and provenance are required?
- Which state does it own, read, mutate, replicate or cache?
- What are startup, shutdown, expiry, cancellation and upgrade semantics?
- What happens on timeout, partial completion, duplicate request, crash, partition and uncertain acknowledgement?
- Which limits bound CPU, memory, tokens, fan-out, storage, retries, time and money?
- What is observable and audited, and what sensitive data must not be logged?
- What are the threat, abuse, misuse and safety cases?
- How is it isolated, backed up, restored, migrated and decommissioned?
- What is its compatibility and deprecation contract?
- What measurable evidence would later establish contract satisfaction?

## 7. Repository discovery protocol

The source inventory must include more than obvious source modules:

1. Full tracked tree: source, tests, docs, examples, scripts, migrations, schemas, assets and generated files.
2. Build/runtime manifests: packaging, Android/Gradle, lockfiles, containers, build definitions and toolchains.
3. CI/CD and automation: workflows, release pipelines, secret references, permissions, artifact retention and deployment configuration.
4. Entry points and invocation graph: imports alone are insufficient; trace constructors, factories, registries, callbacks, CLI/API routes, event handlers and background workers.
5. Persistence and external I/O: databases, files, caches, queues, network clients, subprocess boundaries, device APIs and third-party providers.
6. Configuration and environment: defaults, precedence, secret injection, feature flags, tenant settings and unsafe fallback behavior.
7. Tests and fixtures: evidence of intended behavior, not proof that untested paths or production deployments are complete.
8. Existing architecture references: reconcile overlapping and historical documents; preserve provenance and identify stale claims.
9. Product requirements: include capabilities described in plans even when no implementation path exists.
10. External dependencies: trust, availability, licensing, data handling, versioning and exit strategy.

Search results and filename matches are discovery leads, not exhaustive proof. Every source review records inspected ref/commit, paths and scope.

## 8. Closure evidence per workstream

A workstream is not closed until it has:
- complete source/capability inventory with explicit inspected scope;
- one primary owner per responsibility and documented shared contracts;
- authority, identity and trust dependencies mapped;
- canonical data, state and event lifecycles;
- normal, failure, degraded, cancellation and recovery paths;
- threat, privacy, safety and abuse cases;
- bounded resource and operational assumptions;
- versioning, compatibility, migration and deprecation rules;
- explicit decisions or deferred items with owner and rationale;
- traceability from requirements to components to later acceptance criteria.

No 100% score is permitted while any in-scope category remains UNKNOWN. DEFERRED is transparent, not equivalent to complete.

## 9. Current cycle findings and priorities

ADR-002 through ADR-005 remain proposals. Unresolved evidence includes runtime call-site/constructor inventory, all persistence namespaces and recovery consumers, every direct agent invocation, and provider/placement ownership.

The source traceability ledger identifies crypto-related families including core/crypto.py, core/key_lifecycle.py, core/secure_channel.py, core/identity.py, core/attestation.py, core/trust_chain.py, core/secure_boot.py, core/multiauth.py, core/authorization_replay.py, core/security_integration.py, core/secure_memory.py and core/secure_storage.py. This is a discovery inventory only. It does not establish complete key custody, algorithm agility, rotation under partition, trust-root recovery, certificate lifecycle, hardware-backed protection or post-quantum migration.

The next reconciliation cycle must treat W01/W09 cryptographic authority and trust lifecycle, W02/W03 runtime-state lifecycle, W04/W05 invocation/resource lifecycle, and W06 evidence/semantic lifecycle as coupled design clusters while continuing W07–W12 discovery in parallel.

## 10. Freeze prohibition

Architecture freeze is prohibited while an in-scope plane or cross-cutting capability is UNKNOWN; a source family is unclassified; authority or state ownership is contradictory; a required failure/recovery path is undefined; a critical assumption has no owner/disposition; traceability is broken; or the architecture depends on unbounded or implicit behavior.

This register does not authorize integration, implementation, testing, deployment or merge. Those phases begin only after explicit architecture-freeze approval.

## Additional gaps discovered — 2026-11-22

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-INGRESS-01 | conflicting / ambiguous | `web/app.py`: direct `/api/chat` vs gateway-authenticated `/v1/execute` | Route-by-route canonical ingress/auth policy and upstream enforcement evidence |
| G-CONTEXT-01 | unbounded trust / incomplete provenance | `jarvis/context/authorized.py` | Versioned source manifest, tenant/purpose scope, consent, classification, retention and attestation |
| G-OBSERVATION-01 | unverified / stale evidence | `jarvis/observation/fabric.py` | Trusted capture time, monotonic sequence, digest/signature, freshness and anti-replay |
| G-PERCEPTION-01 | authority ambiguity | `jarvis/perception/audio.py` | Keep wake event separate from identity, explicit user intent and ActionGate authorization |
| G-CONSENT-01 | incomplete lifecycle | `core/user_understanding.py` | Durable purpose-specific consent, inference lineage, correction, deletion and tombstones |
| G-CYBER-01 | weak authorization evidence | `core/cyber_range.py` | Signed owner authorization and independent Reality Bridge policy gate |
| G-DEVICE-01 | local-only selection | `core/device_fabric.py` | Attested enrollment, leases, revocation, capacity/residency-aware selection |
| G-DISTRIBUTED-01 | declared-not-proven security | `core/distributed.py` | Cryptographic shard manifest, key custody, replication and anti-rollback |
| G-SCALE-01 | in-memory control-plane primitive | `ecosystem/global_scale.py` | Durable queue, atomic capacity lease, fencing, deduplication and reconciliation |
| G-PROVIDER-01 | underspecified adapter contract | `jarvis/providers/base.py` | Versioned typed provider contract, usage, privacy, timeout, cancellation and idempotency |

These are architecture discovery findings, not test-proven defects.

## Additional assurance and operational gaps — 2026-11-23

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-SECOPS-01 | local-only / non-durable | `core/observability.py` | Authenticated durable events, trusted sequence, incident and containment owners |
| G-EGRESS-01 | enforcement ambiguity | `core/egress.py` | Prove mandatory mediation and close DNS/redirect/proxy/socket bypasses |
| G-SUPPLY-01 | incomplete provenance | `core/supply_chain.py` | SBOM, builder provenance, signer lifecycle, independent approvals and rollback |
| G-SELF-01 | governance boundary unresolved | `core/self_improvement.py` | Independent external admission, protected zones and release signer separation |
| G-OFFLINE-01 | digest mistaken for authenticity risk | `core/offline.py` | Signed snapshot, device/tenant binding, trust root and bounded revocation freshness |
| G-OUTBOX-01 | in-memory / indeterminate effects | `core/offline.py` | Durable outbox, receipt, deduplication, delivery semantics and reconciliation |
| G-ANCHOR-01 | hardware root absent | `core/offline_anchor.py` | Protected storage/TPM/HSM or explicit reduced-assurance mode |
| G-SEMANTIC-01 | structural verification overclaim | `core/verification.py`, `core/reasoning.py` | Evidence-backed semantic and domain validation levels |
| G-CONFIDENCE-01 | uncalibrated score | `core/metacognition.py`, `core/universal_intelligence.py` | Name score semantics and establish calibration/validation protocols |
| G-FREEZE-01 | structural completeness conflated with closure | `core/architecture_gate.py` | Separate source/callsite/deployment/evidence-backed freeze manifest |
| G-DOMAIN-01 | specialist qualification missing | `core/universal_intelligence.py` | Domain manifests, jurisdiction, qualified review and liability ownership |

These are architecture discovery findings, not test-proven defects.

## Additional four-front, memory and ecosystem gaps — 2026-11-23

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-FRONT-ID-01 | unsafe default / identity ambiguity | `ecosystem/boundaries.py` | Front labels cannot substitute for issuer-verified principals |
| G-DISPATCH-01 | coarse lifecycle / idempotency ambiguity | `ecosystem/runtime_dispatch.py` | Separate intent/idempotency/execution/action/receipt and indeterminate outcomes |
| G-MEMORY-REPLICA-01 | declared redundancy | `ecosystem/global_fabric.py` | Verify replica identity, health, independent failure domains and content digest |
| G-MEMORY-DELETE-01 | incomplete data lifecycle | `ecosystem/global_fabric.py` | Tenant isolation, retention, tombstones and anti-resurrection across tiers/backups |
| G-AUTH-INDEX-01 | local cache mistaken for authority | `ecosystem/global_fabric.py` | Signed issuer chain, expiry, epoch, revocation and cache freshness |
| G-PRODUCT-IMPL-01 | architecture intent vs implementation ambiguity | `architecture/BUSINESS_PROJECT_FABRIC.md`; inspected `ecosystem/` inventory | Classify payment/ledger/marketplace/community as implemented, external, planned or unknown |
| G-FUNDS-SEG-01 | ownership/ledger boundary | Business Project Fabric | Segregated beneficial ownership, regulated payment boundary, double-entry settlement and disputes |
| G-COMMUNITY-GOV-01 | governance and safeguarding | Community architecture requirements | Membership/appeal/conflict/safety/compensation/exit and independent fund audit |
| G-IMPACT-MEASURE-01 | impact measurement overclaim risk | Environmental/community architecture requirements | Baseline, boundary, net impact, uncertainty and independent measurement |

These are architecture discovery findings, not test-proven defects.


## Additional agent/runtime lifecycle gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-AGENT-OWNER-01 | overlapping authority/dispatch surfaces | `core/agent_fabric.py`, `core/operational_fabric.py`, `core/coordination.py`, `core/agent_mesh.py` | Complete constructor/call-site graph; define registry, selection, delegation, execution, admission and commit owners |
| G-AGENT-MESH-01 | discovery label exceeds enforcement evidence | `core/agent_mesh.py` | Define authenticated membership, capabilities, liveness lease, capacity and policy enforcement or retain as role lookup only |
| G-AGENT-LIVE-01 | local heartbeat mistaken for distributed liveness | `core/agent_runtime.py` | Signed heartbeat, lease expiry, failure detector, fencing and partition semantics |
| G-AGENT-CAPACITY-01 | plan truncation semantics unresolved | `core/coordination.py` | Reject, queue, wave-delegate or explicitly defer excess steps; never silently imply whole-plan completion |
| G-CONSENSUS-TYPE-01 | universal equality consensus overreach | `core/coordination.py` | Typed comparison, uncertainty, evidence independence and domain-specific disagreement handling |
| G-DAG-PARALLEL-01 | topological order confused with parallel execution | `noryx7_runtime/scheduler.py`, `noryx7_runtime/engine.py` | Specify bounded concurrent executor, dependency barriers, conflicts, cancellation, fairness and deterministic admission |
| G-EFFECT-UNKNOWN-01 | FAILED does not prove no external side effect | `noryx7_runtime/engine.py`, `noryx7_runtime/contracts.py` | Add indeterminate/reconciliation states, idempotency and authoritative adapter receipts; prohibit blind retry |
| G-PLANE-FREEZE-01 | path existence confused with architecture closure | `core/architecture_gate.py`, `core/architecture_registry.py` | Separate structural gate from evidence-backed source/callsite/boundary/test/deployment freeze manifest |

These are architecture discovery findings, not test-proven defects.


## Additional cognitive/evidence/global-scale gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-EVIDENCE-LADDER-01 | assurance levels conflated | `core/evaluation.py`, `core/metacognitive_challenge.py`, `core/verification.py` | Define explicit structural/synthetic/independent/empirical/operational evidence levels and promotion criteria |
| G-EVAL-MANIFEST-01 | evaluation evidence lacks complete governance | `core/evaluation_campaign.py`, `core/evaluation.py` | Signed manifests, evaluator identity, result uniqueness, holdout controls, statistical power and durable approval |
| G-FINCH-CALIBRATION-01 | heuristic forecast can be mistaken for probability | `core/finch.py` | Temporal backtest, base rates, calibration, confidence intervals, drift and provenance |
| G-MIRROR-DOMAIN-01 | physical/domain simulation validity unproven | `core/reasoning.py`, `core/finch.py` | Domain-specific model validation, uncertainty, external holdout and Reality Bridge safety |
| G-MEDIA-CUSTODY-01 | media digest/locator is not secure custody | `core/multimodal.py` | Authenticated locator, encryption, consent, tenant, retention/deletion and lineage |
| G-GLOBAL-DURABILITY-01 | global fabric primitives are local/in-memory | `core/distributed.py`, `ecosystem/global_scale.py` | Durable queues, authenticated membership, leases, replication, autoscaling, quotas and DR |
| G-RESEARCH-EGRESS-01 | HTTPS fetch not equivalent to safe egress | `core/frontier_capabilities.py` | DNS/IP and redirect policy, private-address denial, content isolation, source trust and provenance |
| G-PROVIDER-ATTEST-01 | provider `verified` field is self-asserted | `core/frontier_capabilities.py` | Signed receipts, response/quote binding, replay/idempotency, human confirmation and reconciliation |
| G-COLLAB-INDEPENDENCE-01 | agent diversity not equivalent to independent evidence | `core/collaboration.py` | Model/provider/evidence lineage, independent source policy and disagreement adjudication |

These are architecture discovery findings, not test-proven defects.


## Additional NEXUS, research, specialist and impact gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-CLAIM-LINEAGE-01 | semantic lineage absent from inspected verifier path | `core/verification.py`, `core/reasoning.py` | Typed claims, source spans, immutable artifact identity, support/contradiction links, temporal validity and reviewer scope |
| G-SOURCE-AUTHORITY-01 | source authenticity/authority not established by digest | `core/frontier_capabilities.py` | Authenticated publisher/source identity, authority scope, capture time, correction/retraction and source independence |
| G-EGRESS-REDIRECT-01 | network destination enforcement incomplete in inspected fetch path | `core/frontier_capabilities.py` | DNS/IP/private-address controls, redirect revalidation, proxy handling and mandatory egress mediation |
| G-CONTENT-INSTRUCTION-01 | retrieved content can cross trust boundary | `core/frontier_capabilities.py` | Explicit untrusted-data/instruction separation, parser isolation and prompt-injection-resistant ingestion contract |
| G-SPECIALIST-QUAL-01 | routing label can be mistaken for qualified competence | `core/universal_intelligence.py`, `core/subtask_uif.py` | Versioned qualification manifest, independent assessment, jurisdiction, validity/expiry and escalation |
| G-SUBTASK-SEMANTIC-01 | structural subtask verification can be mistaken for semantic truth | `core/subtask_verification.py` | Bind each result to evidence, semantic validator, reviewer and exact claim scope |
| G-PROVIDER-RECEIPT-01 | provider response integrity and effect certainty incomplete | `core/frontier_capabilities.py` | Signed receipt binding request/response/quote/recipient/amount/time/idempotency and reconciliation |
| G-MODEL-VALIDITY-01 | simulation validity not established by structural feasibility | `core/reasoning.py`, `core/finch.py` | Model manifests, calibration, independent validation, uncertainty, OOD envelope and field transfer criteria |
| G-IMPACT-BASELINE-01 | project activity can be misreported as net impact | domain assurance and community architecture | Baseline, counterfactual, additionality, leakage/rebound, lifecycle boundary, uncertainty and independent measurement |
| G-CONTRIBUTOR-SAFETY-01 | contributor safeguards/fair compensation not evidenced in inspected ecosystem modules | `ecosystem/` inventory; community requirements | Voluntary terms, safety/insurance, safeguarding, grievance, stop-work authority, compensation and exit |
| G-FUNDS-LEDGER-02 | fund categories and project restrictions lack source-level ledger trace in inspected scope | `architecture/BUSINESS_PROJECT_FABRIC.md` | Beneficial ownership, segregated funds, double-entry ledger, payment reconciliation, refunds/disputes and independent audit |

These are architecture discovery gaps, not test-proven defects. The inspected `ecosystem/` directory is not a claim about all repository subtrees or external services.


## Additional ingress, memory, offline and operational trust gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-SESSION-PRINCIPAL-02 | identity binding incomplete | `gateway/auth.py`, `gateway/runtime_adapter.py` | Bind session to enrolled principal, issuer, device/workload, audience, scope, key ID and revocation epoch; client_id is metadata only |
| G-SESSION-REVOCATION-01 | revocation lifecycle absent in inspected token authority | `gateway/auth.py` | Server-side session registry or revocation epoch, logout/compromise handling, key rotation and nonce/replay policy |
| G-MEMORY-CONTEXT-SCOPE-01 | context hydration not execution-scoped | `core/context.py` | Apply explicit execution/principal/tenant scope and record authorized sharing grants |
| G-MEMORY-DEGRADED-01 | silent empty-context fallback | `core/context.py` | Typed complete/empty/partial/stale/denied/unavailable state; prohibit silent downgrade for critical tasks |
| G-OFFLINE-DURABILITY-02 | encrypted queue is process-local | `core/offline.py` | Durable transactional outbox with crash recovery, sequence and signed acknowledgement chain |
| G-OFFLINE-EFFECT-UNKNOWN-02 | pending record can be removed after exception | `core/offline.py` | Preserve intent on uncertain dispatch; reconcile using idempotency key and authoritative receipt; compensate when required |
| G-STATE-ROOT-01 | local digest not independent trust root | `core/state_journal.py` | Protected signed checkpoint/root, key lifecycle and cross-store recovery protocol |
| G-RECOVERY-DISTRIBUTED-01 | recovery lock is process-local | `core/recovery.py` | Define distributed epoch/fencing and behavior across nodes, partitions and restarts |
| G-EGRESS-ENFORCEMENT-02 | allowlist not proven at network boundary | `core/egress.py` | Mandatory socket/DNS/redirect/proxy enforcement and bypass tests after architecture freeze |
| G-PROVIDER-RETRY-SAFETY-01 | generic exception failover may duplicate external effect | `core/provider_router.py` | Typed failure certainty, unique idempotency, receipt and reconciliation before retry |
| G-RESOURCE-PLACEMENT-01 | static resource choice lacks live hard constraints | `core/resource_router.py` | Residency, jurisdiction, capacity, health, cost, energy and quota-aware placement |
| G-RELEASE-PROVENANCE-02 | artifact signature does not cover complete release chain | `core/supply_chain.py`, `core/self_improvement.py` | SBOM/build provenance, independent approvals, signer lifecycle, staged promotion and rollback |
| G-SECURITY-EVENT-DURABILITY-02 | security events are process-local | `core/observability.py` | Durable protected event stream, incident owner, alert acknowledgement and containment audit |
| G-POLYGLOT-DEPLOYMENT-01 | polyglot source presence mistaken for integrated deployment | `render.yaml`, Go/Rust service entry points | Authoritative service inventory, service identity, API compatibility, health, secrets, rollout and DR contracts |

These are architecture discovery gaps, not test-proven defects. The context-scope finding is a source-level observation; no runtime behavior was changed or tested in this architecture-only phase.


## Additional structural gate, secure memory, audit and platform assurance gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-PLANE-GATE-SCOPE-02 | structural predicate overclaimed risk | `core/architecture_gate.py`, `core/architecture_registry.py` | Evidence-backed per-plane manifest with source/callsite/integration/trust/enforcement/test/deployment references and signed approvals |
| G-SECURE-MEMORY-DURABILITY-01 | encrypted interface backed by process-local map | `core/secure_memory.py`, `core/secure_storage.py` | Durable backend, transactional writes, crash recovery, replica consistency and protected key lifecycle |
| G-MEMORY-METADATA-01 | encrypted memory schema incomplete for governance | `core/secure_memory.py` | Tenant/principal, consent/purpose, source artifact, retention/expiry, tombstones and derived-data deletion |
| G-AUDIT-CHECKPOINT-CUSTODY-01 | authenticated checkpoint not externally retained by audit class | `core/audit.py` | Durable append-only event custody, external checkpoint retention, trusted time, signer/key governance and restore proof |
| G-AGENT-SKILL-QUAL-02 | skill registration confused with verified competence | `core/agent_skills.py` | Versioned qualification manifest, scope/jurisdiction, reviewer identity, validity and escalation |
| G-PLATFORM-GRANT-01 | local grants not issuer-attested | `core/platform.py`, iOS adapter | Signed grants, enrollment, hardware attestation, remote revocation and policy freshness |
| G-MOBILE-REPLAY-DURABILITY-01 | consumed-action replay set process-local | iOS adapter | Durable or server-authoritative idempotency/replay record and crash/restore semantics |
| G-BROWSER-ISOLATION-ASSURANCE-01 | static marker scan not runtime security proof | `ecosystem/browser_isolation.py` | Build/dependency/runtime network review, OS permission analysis, WebView threat model and variant coverage |
| G-TERMINAL-IMPLEMENTATION-01 | target architecture not located as implementation in inspected tree | `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md`, recursive tree snapshot | Classify as planned until source/runtime path exists; then trace sandbox, remote identity, cancellation, secret and audit lifecycle |

These are architecture discovery gaps, not test-proven defects. No claim is made about code outside the inspected source snapshot.


## Additional agent/evidence/MIRROR WORLD/global-impact gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-AGENT-DISPATCH-OWNER-02 | overlapping local dispatch authorities | `core/agent_core.py`, `core/agent_fabric.py`, `core/agent_mesh.py`, `core/coordination.py`, `core/operational_fabric.py` | Canonical lifecycle owner, adapters, request/attempt/lease IDs, cancellation/retry/effect and durable receipts |
| G-AGENT-DAG-COVERAGE-01 | assignment truncation semantics | `core/coordination.py` | Explicit DAG scheduler, full step coverage, dependency semantics, concurrency, backpressure and fairness |
| G-CONSENSUS-INDEPENDENCE-02 | distinct agent IDs mistaken for independent evidence | `core/coordination.py` | Independence groups for model/provider/data/team/failure domain and correlated-error policy |
| G-SEMANTIC-EVIDENCE-02 | structural verification marker/output presence not semantic support | `core/verification.py`, `core/subtask_verification.py`, `core/universal_intelligence.py` | Claim-source anchoring, entailment, contradiction graph, calibrated uncertainty and reviewer admission |
| G-EVAL-CAMPAIGN-EVIDENCE-01 | campaign manifest/approval predicate not executed campaign proof | `core/evaluation_campaign.py` | Immutable results, evaluator identity, holdout custody, execution provenance, reproducibility and independent sign-off |
| G-MIRROR-WORLD-VALIDITY-02 | deterministic scenario execution not real-world validity | `architecture/NORYX7_MIRROR_WORLD_ARCHITECTURE.md`, `core/reasoning.py` | Domain model manifests, calibration, independent holdout, uncertainty, OOD envelope and Reality Bridge safety case |
| G-FINCH-FORECAST-CALIBRATION-01 | forecast-shaped output without demonstrated calibration | `core/finch.py` | Fixed target/horizon, leakage-safe temporal holdout, proper scoring, calibration and drift monitoring |
| G-GLOBAL-MEMORY-REPLICA-02 | replica labels counted without independent health/durability proof | `ecosystem/global_fabric.py` | Replica identity/health, failure-domain separation, payload durability, digest agreement and repair protocol |
| G-GLOBAL-IDENTITY-AUTHORITY-02 | local identity/session index not canonical issuer/revocation service | `ecosystem/global_fabric.py` | Issuer chain, tenant/session/device scope, expiry, revocation epoch and freshness policy |
| G-W12-LEDGER-OPERATIONS-01 | finance/community docs are target architecture not service proof | `architecture/BUSINESS_PROJECT_FABRIC.md`, ecosystem inventory | Regulated payment boundary, double-entry ledger, segregated funds, settlement/disputes and independent audit |
| G-W12-IMPACT-OUTCOME-02 | activity counts can be mistaken for net impact | `architecture/NORYX7_NEXUS_RESEARCH_SPECIALIST_DOMAINS_AND_IMPACT_RECONCILIATION.md` | Baseline/counterfactual, lifecycle boundaries, leakage/rebound, uncertainty, independent verification and durability monitoring |

These are architecture discovery gaps, not test-proven defects. W01–W12 remain PARTIAL.


## Additional tool/provider/protocol/effect gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-TOOL-AUTH-CONTEXT-01 | authorization context too narrow at registry seam | `core/tool_protocol.py` | Signed principal/tenant/session/device, policy epoch, target, risk and exact action binding |
| G-TOOL-PROVENANCE-01 | tool@version label is not artifact/lineage provenance | `core/tool_protocol.py` | Immutable artifact/build digest, input/output digest, schema, source and authorization receipt |
| G-PROVIDER-FAILOVER-EFFECT-01 | generic exception treated as retry/failover trigger | `core/provider_resilience.py` | Provider-specific effect certainty, operation lookup, idempotency and compensation state machine |
| G-PROVIDER-IDEMPOTENCY-01 | attempt ID can repeat across separate invocations | `core/provider_resilience.py` | Caller-supplied durable operation ID and provider-supported idempotency key |
| G-HTTP-EGRESS-DNS-01 | URL/TLS/redirect validation not socket/DNS isolation | `core/http_provider.py`, `core/egress.py` | Canonical DNS resolution, resolved-IP policy, pinning and mandatory transport mediation |
| G-TRACE-DURABILITY-01 | execution hash chain exists only in process memory | `core/execution_trace.py` | Durable append-only storage, external checkpoint, trusted time, signer and restore semantics |
| G-TRACE-COMPLETENESS-01 | local chain cannot prove omitted events were never emitted | `core/execution_trace.py` | Independent dispatch receipts, sequence authority and external head anchoring |
| G-PROVIDER-QUALIFICATION-01 | provider selection does not encode residency/semantic equivalence | `core/provider_router.py`, `core/provider_resilience.py` | Signed provider manifest, allowed data class/region, capability equivalence, SLO/cost and revocation |
| G-OFFLINE-PROVIDER-RECONCILIATION-01 | offline queue and provider effect state not shown as one durable lifecycle | `core/offline.py`, provider adapters | Unified intent/idempotency/receipt/indeterminate/remote-reconcile protocol |

These are architecture discovery gaps, not test-proven defects. W01–W12 remain PARTIAL.


## Additional memory, crypto, multimodal and global placement gaps — 2026-11-24

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-MEM-CONTEXT-EXEC-01 | execution scope not propagated into memory query | `core/context.py` | Pass execution ID into storage query; typed hydration result and explicit degraded context |
| G-MEM-CUSTODY-01 | memory schema lacks tenant/consent/retention/deletion lineage | `core/memory.py`, `core/secure_memory.py` | Canonical scoped memory envelope, tombstones and derived-data deletion graph |
| G-MEM-DURABILITY-01 | encrypted backing store remains in-process | `core/secure_storage.py` | Durable encrypted backend, replication, backup/restore and consistency evidence |
| G-KEY-AUTHORITY-01 | key lifecycle metadata does not establish external KMS/HSM authority | `core/key_lifecycle.py`, `core/crypto.py` | External key custody, signer roles, key epochs, rotation and distributed revocation |
| G-ATTEST-REVOCATION-01 | runtime attestation trust freshness/replay lifecycle external | `core/attestation.py`, `core/identity.py` | Durable nonce registry, remote revocation, trust-root rotation and hardware evidence |
| G-MEDIA-LINEAGE-01 | media digest/locator lacks capture provenance and derivative custody | `core/multimodal.py` | Authenticated locator, encrypted object custody, consent, retention and transformation graph |
| G-AGENT-QUALIFICATION-01 | first-match dispatch and declarative skills do not qualify specialist execution | `core/agent_fabric.py`, `core/agent_skills.py` | Signed specialist scope, qualification evidence, health/capacity and independence group |
| G-PLACEMENT-TELEMETRY-01 | static placement thresholds do not admit against live capacity/residency/cost | `core/resource_router.py`, `ecosystem/global_scale.py` | Fresh telemetry, reservations, data residency, energy/cost and failure-domain policy |
| G-GLOBAL-REPLICA-HEALTH-01 | replica labels do not prove independent healthy durable copies | `ecosystem/global_fabric.py` | Replica attestations, read/write quorum, consistency watermark and restore drills |
| G-SUPPLY-CHAIN-PROVENANCE-01 | signed artifact manifest lacks SBOM/build/release signer lifecycle | `core/supply_chain.py` | Build provenance, dependency graph, signer roles/revocation and staged release approvals |
| G-OPS-EVENT-DURABILITY-01 | security event bus is in-process and bounded | `core/observability.py` | Durable append, sequence authority, alert routing, retention and incident response |

These are architecture discovery gaps, not test-proven defects. W01–W12 remain PARTIAL.


## Branching cognition, FRL, reverse engineering and domain operations — 2026-11-24

| Gap ID | Observed gap | Source anchor | Required architecture closure |
|---|---|---|---|
| G-HYP-BRANCH-01 | HypothesisEngine emits one plan-aligned hypothesis per step; no explicit alternative branch lifecycle | `core/hypersynth.py`, `core/reasoning.py`, `core/planning.py` | Branch identity/parentage, assumptions, evidence, budgets, pruning, contradiction and merge semantics |
| G-HYP-SIM-02 | InternalSimulator is structural feasibility check, not calibrated domain simulation | `core/reasoning.py` | Typed domain models, units, parameter provenance, calibration, uncertainty and independent validation |
| G-FRL-KERNEL-01 | MIF/FRL proof architecture is specified but dedicated general proof-kernel runtime is not established in reviewed source inventory | `architecture/NORYX7_CRYPTOGRAPHIC_AND_MATHEMATICAL_INTELLIGENCE_ARCHITECTURE.md` | Formal language/theory, proof object, trusted kernel, independent replay and scoped result states |
| G-EVAL-EXEC-02 | Campaign creates deterministic cases/manifests but does not execute cases or authenticate result producers | `core/evaluation_campaign.py`, `core/evaluation.py` | Signed campaign execution ledger, per-case uniqueness, evaluator identity, holdout custody and statistical plan |
| G-CLAIM-LINEAGE-03 | Evidence source/claim strings and strength fields lack canonical source-span lineage | `core/universal_intelligence.py`, `core/subtask_verification.py` | Immutable source/version, claim spans, typed support/contradiction graph and correction/expiry |
| G-RE-WORKBENCH-01 | Cyber range is synthetic/symbolic; no dedicated authorized reverse-engineering workbench evidenced | `core/cyber_range.py`, `core/sandbox.py` | Signed scope manifest, static/dynamic sandbox, protocol state models, artifact lineage and responsible disclosure |
| G-TERMINAL-RUNTIME-01 | PowerShell/Cloud Terminal is target architecture, not evidenced dedicated runtime | `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md` | Session broker, shell adapter, sandbox, policy, secret boundary, remote attestation and durable audit |
| G-BROWSER-ASSURANCE-02 | Browser isolation scan is static marker check | `ecosystem/browser_isolation.py` | Runtime WebView/device/network threat model and independent platform assurance |
| G-SPECIALIST-QUAL-03 | Domain route/skill label is not qualification or jurisdictional authorization | `core/universal_intelligence.py`, `core/agent_skills.py` | Signed domain manifests, qualification evidence, scope, calibration, expiry and expert escalation |
| G-IMPACT-NET-04 | Activity/output metrics can be confused with verified environmental/community net outcomes | `architecture/NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md`, `architecture/NORYX7_NEXUS_RESEARCH_SPECIALIST_DOMAINS_AND_IMPACT_RECONCILIATION.md` | Baseline/counterfactual, leakage/rebound, independent sampling, uncertainty, safeguards and restricted funds |

All findings remain architecture gaps; no runtime defect or test failure is inferred. W01–W12 remain PARTIAL.


## 2026-11-24 — cognitive branching, formal evidence, MIRROR WORLD and systems understanding reconciliation

- HYPERSYNTH: no general competing-hypothesis tree/branch lifecycle demonstrated; one hypothesis is derived from each plan step; inspected assignments execute sequentially.
- Evidence: output presence/contract checks, generated evaluation manifests and confidence fields do not independently establish semantic truth, source authenticity, campaign execution or calibrated probability.
- FRL/NEXUS: formal proof scope, checker/build trust and empirical-to-formal fidelity must remain distinct; unavailable or untrusted checkers fail closed.
- MIRROR WORLD: model manifests, calibration, independent validation, uncertainty/OOD, drift/expiry and Reality Bridge safety approval remain closure requirements.
- Systems understanding: authorized acquisition, artifact custody, isolated analysis, behavior reconstruction and IP/safety boundaries need one lifecycle; reverse-engineering source path was not found at the inspected path/ref (404), not a repo-wide absence finding.
- Terminal/surfaces: target architecture exists; runtime, scoped capabilities, filesystem/process/egress controls, artifact provenance and offline reconciliation remain to be source-mapped.
- Domains: skill labels are not qualifications; scope, jurisdiction, reviewer independence, expiry and escalation are required.
- Placement: static tier thresholds and bounded global primitives do not prove production scheduling, live health/capacity, residency enforcement or cost/energy optimization.
- W12: ledger, restricted funds, disputes/refunds, safeguards and independently verified net environmental outcomes remain open.
All findings map to existing ADRs B71–B104; W01–W12 remain PARTIAL.


## 2026-11-24 — execution semantics, agent scheduling, provider effects and distributed fabric reconciliation

- HYPERSYNTH couples default plan/action bounds to `max_agents`; plan cardinality, concurrency and action budget need separate semantics.
- AgentCoordinator truncates to `plan.steps[:max_agents]` and creates a fresh execution ID; preserve complete DAG and caller-bound execution identity.
- AgentMesh chooses alphabetically first role match; qualification, liveness, capacity, trust freshness and independence are not scheduler inputs.
- ProviderRouter retries on any exception; must distinguish not-dispatched, rejected, confirmed and indeterminate external effects.
- ProviderExecutionGateway action ID lacks a unique request/operation/attempt binding and its result lacks canonical durable receipt/effect state.
- Offline encrypted queue and global memory/control-plane registries are in-process; encryption and metadata do not prove durable payload custody or distributed health.
- StateJournal local SQLite durability is not an independently witnessed checkpoint; RecoveryController epoch/lock is in-process.
- MediaRef digest/locator is not a custody capability or transformation/consent/retention lineage.
- Egress allowlist does not prove DNS pinning/socket mediation; supply-chain signature verification does not itself provide key lifecycle/SBOM/build provenance.
- Global placement primitives do not prove capacity reservation, distributed leases, live telemetry freshness or production worker orchestration.
All findings map to existing B71–B104; W01–W12 remain PARTIAL.


## 2026-11-24 — domain calibration, specialist qualification, cyber-range assurance and public-impact accounting

- FINCH `Forecast.likelihood` is arithmetic mean severity; no time-to-event model or calibration. Type heuristic scores separately from probabilities and require temporal holdout, proper scoring, calibration and drift lifecycle.
- Universal Intelligence has six explicit domain keyword maps plus general reasoning while the domain architecture catalog specifies thirteen domains; track coverage explicitly without assuming unimplemented modules.
- Specialist routing and skill registration do not establish competence, jurisdiction, expiry, independence or execution authority.
- AgentCollaboration's SHA-256 digests cover generated output strings, not source evidence; distinct agent IDs do not prove independent model/provider/source/failure domains.
- EvaluationMatrix accepts caller pass flags and non-empty evidence strings; campaign manifest/result must bind exact artifact, evaluator, holdout, raw test results and independence.
- CyberRange's synthetic sandbox restriction is useful; OwnerAuthorization lacks target/method/environment/issuer/revocation/single-use scope, and `verified=True` means simulation path completed, not real-world validation.
- W12 needs segregated ledgers, double-entry accounting, independent audit, governance/appeal and impact records with baseline/counterfactual/additionality/leakage/rebound/permanence/uncertainty.
All remain architecture gaps; no domain qualification, calibrated forecast, independent evaluator, cyber validation or payment/impact service is claimed implemented.

## Cross-workstream collision discovery — 2026-11-25

The cross-stream collision and handoff model is consolidated in [Cross-Workstream Dependency and Canonical Ownership Reconciliation](NORYX7_CROSS_WORKSTREAM_DEPENDENCY_AND_CANONICAL_OWNERSHIP_RECONCILIATION.md). Add explicit discovery coverage for: (a) multiple runtime coordinators/facades; (b) identity registries and capability issuers; (c) state stores, journals, memory replicas and recovery consumers; (d) agent/provider/scheduler routing overlap; (e) evidence, audit, telemetry and business-ledger separation; (f) cyber-range/MIRROR WORLD and simulation-to-reality boundaries; (g) offline revocation/state epochs; and (h) product/community records versus runtime authority. These are collision hypotheses until source evidence resolves them. Discovery remains parallel; contract freeze follows upstream dependencies. W01–W12 remain PARTIAL.


## 2026-11-25 — ingress, effects and release-evidence gaps

The [Ingress, External Effects, Release Evidence and Cross-Workstream Closure Reconciliation](NORYX7_INGRESS_EFFECTS_RELEASE_AND_CLOSURE_EVIDENCE_RECONCILIATION.md) deepens existing ADR-B56–B62 without creating duplicate IDs. Track the following as unresolved architecture gaps:
- Gateway-session `/v1/execute` and direct `/api/chat` paths are not proven to share the same route-level authentication boundary; upstream proxy behavior remains unknown.
- ProviderRouter, ProviderExecutionGateway and ResilientProviderExecutor require composed retry ownership; nested retry amplification and duplicate side effects are not resolved.
- Logical operation, attempt, downstream idempotency, dispatch receipt, observed effect and durable commit need distinct identities/states.
- Topological scheduling does not by itself establish bounded parallel execution, resource reservation, cancellation or partial-result joins.
- Structural audit outputs, CI success, architecture acceptance and deployment/release approval need separate evidence schemas and scopes.
- Per-platform artifact provenance and release coverage remain incomplete in the inspected inventory.
These are source-grounded gaps/unknowns, not proof of an exploitable endpoint or a failed production deployment. W01–W12 remain PARTIAL.


## 2026-11-25 — source-level conflict discoveries across W01–W12

See [Source-Level Authority, State and Effect Conflict Reconciliation](NORYX7_SOURCE_LEVEL_AUTHORITY_STATE_AND_EFFECT_CONFLICT_RECONCILIATION.md). Newly explicit gaps:
- Two different `StateJournal` classes exist: `noryx7_runtime.state.StateJournal` (in-memory reservations/attestations used by RuntimeEngine) and `core.state_journal.StateJournal` (SQLite verified-state commits used by StateStore). A canonical adapter/transaction/recovery relationship is not established.
- RuntimeEngine retains reservations after dispatch/commit exceptions, but the six-state execution lifecycle cannot represent indeterminate external effects or reconciliation.
- FastAPI `/api/chat` directly invokes OperationalNORYXRuntime while `/v1/execute` uses the gateway session verifier; deployment proxy equivalence remains unknown. A separate standalone gateway server also exposes gateway routes.
- ProviderRouter, ProviderExecutionGateway and ResilientProviderExecutor implement distinct dispatch/failover paths; no single retry/effect coordinator is demonstrated.
- AgentCoordinator truncates assignment to `max_agents`, runs assignments sequentially and creates its own execution ID; AgentMesh uses lexical-first role routing. Multi-step aggregation and same-task consensus semantics need separation.
- OfflineSyncQueue is in-memory and local failure removes its queued item; durable outbox and uncertain local-effect recovery remain open.
- Runtime dispatch receipt hashes a type representation/exception type, not an independently observed target effect.
These are source-level bounded findings and unknowns, not declarations of exploitable vulnerabilities. W01–W12 remain PARTIAL.


## 2026-11-25 — single-cycle W01–W12 end-to-end reconciliation

See [Single-Cycle W01–W12 End-to-End Architecture Reconciliation](NORYX7_SINGLE_CYCLE_W01_W12_END_TO_END_ARCHITECTURE_RECONCILIATION.md). This concurrent pass reconciles identity/authority, runtime ingress, dual state journals, provider retry/effects, agent selection/scheduling, offline custody, evidence classes, simulation-to-reality, specialist qualification, global placement/release and financial/community impact. It records canonical object families, cross-stream collision targets, linked execution/effect lifecycles and the next constructor/registration/call-site source pass. Findings are bounded to named source snapshots; unknowns are not absence claims. W01–W12 remain PARTIAL; no ADR is silently accepted, no implementation or integration is authorized, and no test campaign, merge, deployment or freeze is claimed.


## 2026-11-25 — constructor, authority, offline and ledger source reconciliation

See [Constructor, Call-Site, Authority, Offline and Ledger Reconciliation](NORYX7_CONSTRUCTOR_CALLSITE_AUTHORITY_OFFLINE_AND_LEDGER_RECONCILIATION.md). Added source anchors identify ActionGate and exact one-shot grants, identity/replay scope, separate runtime and SQLite journals, runtime recovery and recovery epochs, offline encrypted outbox versus durable monotonic anchor, ingress divergence, ExecutionFabric registration and W12 fund-segregation architecture. Durable anti-rollback is present; the inspected outbox remains in-memory. Existing tests are evidence of test specifications, not tests executed. W01–W12 remain PARTIAL.


## 8. Newly reconciled cross-plane gaps — 2026-11-25

| Gap | Affected streams | Evidence/impact | Required closure artifact |
|---|---|---|---|
| Authority composition and principal normalization | W01/W02/W07/W08/W09 | Core identity, action grants, gateway sessions, JARVIS authorization and global session/device authorization are separate local authorities | Constructor profile matrix, composition root, canonical PrincipalAssertion and revocation/freshness contract |
| Cross-journal transaction ownership | W02/W03/W08/W09 | Runtime reservation/attestation journal and SQLite verified-state journal have different durability and recovery semantics | Operation transaction state machine and crash/restart reconciliation matrix |
| Effect certainty and retry multiplication | W02/W05/W08/W11 | Provider routing, execution gateway and resilience wrapper expose distinct retry behavior; raw exceptions do not prove no target effect | Single retry coordinator, typed effect outcomes and target idempotency/compensation contract |
| Agent lineage and incomplete assignment | W04/W05/W07/W11 | Assignment is bounded by max_agents; execute creates a new execution ID and runs sequentially; consensus requires exact output equality | Parent-child DAG lineage, overflow policy, concurrency/lease/cancel/join and typed consensus contract |
| Offline queue durability | W03/W08/W09 | Snapshot anti-rollback anchor is durable, but the inspected outbox and acknowledgement deletion are process-local | Durable outbox/inbox, signed remote receipt, replay and crash-safe acknowledgement contract |
| Global memory/placement operationalization | W03/W05/W08/W09 | Replica IDs and placement primitives do not establish replica acknowledgement, durable payload custody or resource leases | Storage/replication adapter contract, consistency model, placement lease and node attestation |
| W12 financial and impact execution authority | W07/W09/W10/W12 | Tree inventory did not establish production ledger/payment/escrow implementation; business/project architecture remains proposal-level evidence | Double-entry ledger, segregation, payment/escrow controls, reconciliation and independent impact methodology |
| Release provenance and rollback | W09/W11 | CI workflow and signed manifest verifier do not establish source-to-artifact-to-deployment chain or staged rollback | Signed provenance chain, builder identity, SBOM, approval quorum, promotion and rollback evidence |

These are architecture gaps to resolve, not assertions that no external integration exists. W01–W12 remain PARTIAL; no gap is closed by path presence alone.


## 9. Memory, multimodal and surface gaps — 2026-11-25

| Gap | Streams | Closure requirement |
|---|---|---|
| Memory custody and durable hydration | W03/W06/W08/W09 | tenant/principal/session/execution scope, source lineage, purpose/consent, retention/deletion, durable backend and typed partial/stale/error outcomes |
| Key governance | W02/W03/W08/W09 | production KMS/HSM, key version/rotation, compromise/revocation, backup/restore and offline-device recovery |
| Multimodal provenance | W06/W08/W09/W10 | authenticated source/capture, rights/consent, immutable transforms, timestamps/segments and claim-to-source verification |
| Model evidence and independence | W02/W04/W05/W06/W10 | invocation provenance, correlated-provider analysis, calibrated verification and typed evidence admission |
| Tool protocol convergence | W02/W04/W05/W07/W08 | converge callback-authorized ToolRegistry and ActionGate ToolExecutor on canonical ActionSpec/effect lifecycle |
| Device and placement attestation | W05/W07/W08/W09/W11 | signed device/node identity, remote revocation, capacity lease, fencing, residency and completion receipt |
| Browser surface assurance | W07/W08/W09 | runtime sandbox, network egress, URL/origin, downloads, cookie/session custody and update rollback evidence |
| Durable observability | W08/W09/W11 | durable tamper-evident events, trace lineage, delivery acknowledgement, alerting and incident containment |

These are architecture gaps, not claims that no external backend or provider exists. W01–W12 remain PARTIAL.


## 10. Product-level capability and realization gaps — 2026-11-25

| Gap | Streams | Why it matters | Required closure |
|---|---|---|---|
| Product intent versus operational guarantee | W01–W12 | A capability may be specified and have source files without one reachable, governed production path | Per-capability owner, composition/call-site map, runtime boundary, failure model and acceptance evidence |
| End-to-end object chain | W01/W02/W03/W04/W05/W07/W08/W09 | Principal, interaction, evidence, cognitive run, plan, delegation, action, effect, verification and commit are not yet one canonical versioned chain | Canonical schemas, IDs, state transitions, migration/compatibility and cross-plane conformance |
| Cognitive branching versus execution concurrency | W04/W05/W07/W08 | Cognitive phases and plan DAGs exist, but scheduler output is consumed sequentially by RuntimeEngine | Bounded concurrent executor, lease/conflict model, cancellation, partial-result semantics and deterministic audit |
| Semantic evidence and specialist qualification | W04/W06/W10/W12 | Structural verification and keyword specialist routing do not establish source entailment, calibration or professional competence | Claim-span evidence, authenticated sources, calibration, qualification registry and human escalation |
| MIRROR WORLD reality validity | W06/W10/W11 | Deterministic or synthetic simulation does not establish real-world predictive validity | Domain kernel manifests, calibration/holdout, uncertainty, OOD limits and isolated Reality Bridge safety case |
| Systems reverse-engineering realization | W06/W07/W08/W10 | Architecture intent and synthetic cyber-range code do not establish a general authorized system-understanding engine | Asset authorization manifest, passive/active tiers, instrumentation isolation, protocol evidence and report standard |
| Global operating guarantees | W03/W05/W08/W09/W11 | Local registries, replica labels and resource selection do not prove durable global service | Durable multi-region control/data plane, signed node trust, capacity leases, replication acknowledgements and DR evidence |
| W12 delivery and public impact | W07/W09/W10/W12 | Community and financial architecture is not proof of live payment, custody, ledger or independently verified environmental/social outcomes | Regulated financial controls, double-entry/reconciliation, independent impact baseline/counterfactual and field evidence |

This register is a design/closure inventory, not a claim that no external service exists. W01–W12 remain PARTIAL; no implementation, test campaign or freeze is authorized by this entry.


## 11. Agent, evidence, simulation and release assurance gaps — 2026-11-25

| Gap | Streams | Closure requirement |
|---|---|---|
| Structural gate mistaken for architecture closure | W01–W12 | Separate path-presence checks from contract conformance, constructor/call-site integration and acceptance evidence |
| Agent role selection and assignment completeness | W01/W04/W05/W10 | Qualification manifest, full plan coverage, overflow policy, parent-child lineage, independent verifier and capacity-aware scheduling |
| Sequential coordinator and consensus semantics | W02/W04/W05 | Bounded concurrent DAG execution, leases, cancellation/join, partial outcomes and semantic consensus preserving dissent |
| Structural evidence promoted to truth | W06/W10 | Typed claims, immutable source spans, entailment/contradiction edges, calibrated uncertainty and reviewer lineage |
| MIRROR WORLD source-to-reality validity | W06/W07/W10 | Implemented domain kernels, source custody, independent holdouts, calibration, OOD policy and isolated Reality Bridge |
| Cyber range generalized beyond sandbox | W07/W08/W09 | Explicit authorized asset manifests, passive/active tiers, safe acquisition, production isolation and reproducible evidence |
| FINCH forecast probability interpretation | W06/W07/W10/W11 | Target definitions, temporal holdouts, proper scoring, calibration curves, uncertainty and independent field validation |
| Evaluation campaign evidence independence | W06/W10/W11 | Campaign execution, evaluator identity, holdout custody, leakage controls, reproducibility and approval evidence |
| Provider retry and uncertain side effects | W02/W08/W09/W11 | Single retry coordinator, idempotency, typed uncertain-effect state, authenticated target receipt and reconciliation |
| Dispatch receipt overclaim | W01/W02/W08/W09 | Separate acceptance, returned payload digest, signer identity, observed effect and verified commit |
| Browser source scan overclaim | W08/W09/W11 | Runtime sandbox/OS boundary, egress mediation, origin/session/download controls and adversarial platform evidence |
| Signed manifest versus full release provenance | W09/W11 | Trusted builder, dependency/SBOM, key lifecycle, approval quorum, deployment identity, promotion and rollback chain |

These are architecture gaps, not claims that no external provider or service exists. W01–W12 remain PARTIAL.


## 2026-11-25 — additional source-reconciled gaps

| Gap | Workstreams | Required architecture closure |
|---|---|---|
| Core/JARVIS memory duplication and storage semantics differ | W03/W08/W09 | Canonical memory ownership, adapter/migration contract, tier backend, namespace, retention and restore matrix |
| Encrypted memory is not necessarily durable memory | W03/W09/W11 | Durable backend, backup/restore, replication, key rotation, deletion/tombstone propagation and recovery evidence |
| Offline queue durability is distinct from monotonic anchor durability | W02/W03/W08/W09 | Durable outbox/inbox/ack lifecycle, idempotent sync, conflict resolution and replay-safe recovery |
| Provider paths have divergent selection, action IDs and retry behavior | W02/W04/W05/W08/W09 | Unified logical operation/idempotency identity, attempt model, dispatch/effect certainty and signed adapter receipts |
| ToolRegistry and ToolExecutor have different authorization/result contracts | W01/W02/W08/W09 | Canonical ToolSpec/ActionSpec, principal/tenant binding, result evidence and effect lifecycle |
| Model fan-out/provenance does not establish independence or correctness | W04/W05/W06/W10/W11 | Model/source lineage, common-cause groups, independent evaluation and calibrated confidence |
| FINCH forecast likelihood is heuristic | W06/W07/W10/W11 | Forecast target/horizon/calibration cohort, probability distribution, proper scoring and drift evaluation |
| NEXUS source citations lack a single fully established custody graph | W06/W09/W10 | SourceArtifact/SourceSpan, immutable acquisition, exact extraction spans, contradiction/correction/retraction graph |
| Formal proof, empirical observation and simulation output can be conflated | W06/W07/W10 | Typed epistemic artifacts, checker identity and explicit limits of proof/model assumptions |
| Cyber range does not constitute general authorized reverse engineering | W07/W08/W09/W10 | Asset authorization manifest, passive/active tiers, sandbox, egress limits, stop conditions and signed findings |
| Browser source scan is not runtime containment | W08/W09/W11 | Process/OS sandbox, origin and download policy, network egress mediation and adversarial validation |
| Artifact signature is not full release provenance | W09/W11 | Builder identity, dependency/SBOM, approval, artifact promotion, deployment attestation and rollback chain |
| W12 financial and environmental impact evidence remains separate | W10/W11/W12 | Segregated double-entry ledger, payment reconciliation, independent outcome measurement and dispute/audit workflow |

These are unresolved architecture gaps, not claims that no external system or service exists. W01–W12 remain PARTIAL.
