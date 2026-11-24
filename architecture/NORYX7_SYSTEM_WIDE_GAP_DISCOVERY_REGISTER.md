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
