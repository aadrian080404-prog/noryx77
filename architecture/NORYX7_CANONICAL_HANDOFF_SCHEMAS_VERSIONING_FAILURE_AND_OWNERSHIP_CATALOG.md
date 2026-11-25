# NORYX7 — Canonical Handoff Schemas, Versioning, Failure and Ownership Catalog

**Review date:** 2026-11-25  
**Basis:** HEAD `0089d3c47f0be62cf3424beb5eaaf3c41319a1eb`; existing canonical plane contracts, cross-cutting contracts, dependency DAG, source reconciliations and realization inventory.  
**Mode:** architecture-only contract convergence across W01–W12.  
**Boundary:** no source/runtime/test/dependency/workflow/config/deployment changes; no ADR acceptance; no architecture freeze.

## 1. Purpose and closure status

The repository already contains plane-level contracts and multiple system-wide reconciliations. This catalog does not introduce a competing plane taxonomy or a second runtime design. It makes the handoffs explicit: every boundary has a producer, consumer, authority, identity continuity, durable record, failure semantics and acceptance evidence.

The purpose is to reduce repeated discovery and prevent locally reasonable designs from disagreeing at system boundaries.

**Current status:** W01–W12 remain PARTIAL. Existing ADRs and B-series decisions remain OPEN unless accepted by their governing process.

## 2. Normative contract rules

1. Every cross-plane message is a versioned envelope; untyped dictionaries and free-form metadata are not authority.
2. A producer may assert only facts it is authorized to attest. A consumer validates issuer, audience, schema, scope, freshness, signature where required, and policy epoch.
3. Identity, authority, execution identity, evidence identity and storage identity are distinct types even when represented as strings.
4. Correlation IDs connect records; they do not grant access or prove common authority.
5. A digest proves byte identity relative to the hashed bytes, not truth, publisher authority, consent or semantic entailment.
6. A successful local function return does not prove remote effect, durable commit, or downstream acceptance.
7. Unknown, partial, stale, unavailable and denied are explicit outcomes; none is silently converted to success, empty, false or retryable.
8. Retries preserve logical operation identity and use a new attempt identity. Non-idempotent effects require target reconciliation or explicit human resolution when outcome is uncertain.
9. Every durable record has an owner, retention/deletion rule, integrity mechanism, backup/recovery path and access policy.
10. Version changes are additive only when old consumers remain safe. Breaking semantic changes require a new major schema or explicit adapter and migration plan.
11. Security policy can narrow capability but no transport, router, scheduler, model, agent or business service can widen it.
12. Evidence used for acceptance must name exact source/build/configuration, producer, verifier, scope and freshness.

## 3. Canonical envelope family

These are normative logical contracts, not a claim that the repository already implements these exact classes.

### 3.1 Common envelope

| Field | Type/meaning | Rule |
|---|---|---|
| schema_id | stable contract identifier | required |
| schema_version | major.minor.patch | required; explicit compatibility policy |
| record_id | immutable record identity | unique within issuer namespace |
| record_type | closed typed discriminator | required; no implicit coercion |
| issuer | typed Principal/Agent/Device/Service identity | authenticated and authorized for record type |
| audience | intended consumer/service/domain | exact or explicitly scoped |
| tenant_scope | tenant/org/project boundary | mandatory where multi-tenant data exists |
| created_at / expires_at | trusted time bounds | clock source and skew policy declared |
| policy_epoch | policy/revocation epoch | stale epoch handling explicit |
| correlation | request/operation/trace references | correlation only, not authority |
| payload_digest | digest of canonical payload | algorithm and canonicalization version declared |
| signature | optional/required authenticated signature | issuer key ID, algorithm, epoch and verification path |
| classification | data sensitivity and residency class | drives storage, routing and egress |
| provenance | parent records and transformations | immutable lineage edges |
| status | typed lifecycle state | state transitions validated |

A consumer rejects unsupported major versions, unknown critical fields, invalid issuer/audience/scope, expired records and stale policy epochs. Unknown non-critical extensions may be retained only under explicit compatibility rules.

### 3.2 Identity and authority records — W01

**PrincipalAssertion**: subject, tenant, issuer, authentication method/assurance, audience, session, device/workload binding, issued/expiry times, policy epoch, revocation handle, source surface and authentication context.

**DelegationGrant**: grant ID, delegator, delegate, principal lineage, exact task/action scope, resource/data scope, constraints, expiry, revocation epoch, attenuation chain and issuer signature.

**CapabilityDecision**: decision ID, principal, agent, exact capability/action/resource, target, parameters digest, policy version, allow/deny, obligations, expiry, replay nonce and evaluator identity.

Rules:
- session authentication is not an unrestricted tool grant;
- an agent identity is not a user identity;
- a device identity is not proof of user consent;
- capability grants are exact, short-lived, attenuated and replay-controlled;
- revocation freshness is bounded and enforced at the privileged action boundary.

### 3.3 Operation and execution records — W02

**OperationEnvelope**: request ID, stable operation ID, requester principal, objective, constraints, deadline, idempotency scope, consent/purpose, data classification and cancellation authority.

**ExecutionEnvelope**: operation ID, coordinator-issued execution ID, plan ID/version, parent execution, attempt group, policy epoch, budget, selected composition profile and lifecycle state.

**StepInvocation**: plan/step ID, dependencies, agent/tool/provider target, input digest, delegation lease, attempt ID, deadline and expected result schema.

Rules:
- one operation may have multiple execution attempts; attempts never replace operation identity;
- child tasks inherit operation and execution lineage from coordinator, not self-asserted IDs;
- plan versions are immutable once execution begins; replanning creates a new version and records why;
- scheduler order is not proof of parallel execution or successful completion.

### 3.4 Authorization and dispatch records — W01/W02/W05/W09

**ActionIntent**: action ID, operation/execution/step IDs, principal, actor, exact action, target, parameter digest, risk class, requested effects and deadline.

**AuthorizationReceipt**: decision ID, evaluator, policy version/epoch, exact action/target binding, obligations, expiry and replay nonce.

**DispatchAttempt**: attempt ID, action ID, provider, destination, idempotency key, dispatch time, transport outcome and response digest.

**EffectReceipt**: target/provider identity, provider operation ID, accepted/rejected/unknown state, observation method, external effect evidence, signer and reconciliation status.

Rules:
- dispatch receipt and effect receipt are different types;
- attempt failure before dispatch may be retryable; timeout after dispatch may be UNKNOWN;
- retry controller is singular for a given provider path; nested retry layers must not multiply attempts without a shared budget and idempotency key;
- target idempotency guarantees must be documented per action class, not assumed globally;
- compensation is a new authorized action linked to the original effect, not deletion of history.

### 3.5 State, memory and audit records — W03/W09

**StateCommit**: transaction ID, operation/execution IDs, expected prior version, committed version, journal sequence, state digest, writer identity, schema version and commit proof.

**MemoryRecord**: record ID, tenant/principal/agent scope, memory class/tier, purpose, source lineage, content digest, encryption key ID/version, consent/retention/deletion policy and retrieval status.

**AuditEvent**: event ID, actor, action, object, decision, before/after digests, timestamp, sequence, integrity link, sensitivity and retention.

Rules:
- memory, evidence, security audit, financial ledger and domain state are separate custody classes;
- missing storage is UNAVAILABLE, not EMPTY;
- reads return COMPLETE/PARTIAL/STALE/DENIED/UNAVAILABLE/EMPTY with completeness metadata;
- deletion creates verifiable tombstones and propagates to replicas, indexes, derived caches and backups according to policy;
- append-only audit correction is a superseding event, not silent mutation;
- a verified state commit does not prove an external provider effect.

### 3.6 Agent delegation and result records — W04

**AgentQualification**: agent identity, skill/domain scope, evidence references, issuer, validity period, jurisdiction, constraints, revocation and reviewer independence.

**DelegationLease**: lease ID, parent execution, child step, agent, principal lineage, exact task/resources, policy epoch, capacity reservation, expiry, fencing token and cancellation handle.

**AgentResult**: task/step identity, agent identity, lease ID, output schema/digest, evidence references, limitations, dissent, execution provenance and proposed status.

**ResultAdmission**: verifier identity, required coverage, policy version, provenance checks, semantic checks, independence class, accepted/partial/rejected/indeterminate status and reason.

Rules:
- registration does not equal qualification; qualification does not equal authority;
- selection requires role/skill fit plus trust, freshness, capacity, jurisdiction, privacy and independence;
- a missing agent cannot silently truncate the plan;
- quorum counts only independent failure domains under a declared independence policy;
- dissent and partial results are retained and visible.

### 3.7 Routing, provider and capacity records — W05/W11

**ProviderDispatchPlan**: provider/model, capabilities, data class, region, cost/latency ceilings, fallback set, idempotency behavior, trust profile and budget.

**PlacementLease**: node/region, workload, resource reservation, residency/jurisdiction, attestation, expiry, fencing token, quotas, energy/cost budget and failover policy.

Rules:
- agent selection, model selection, provider selection and physical placement are separate decisions;
- a model response is a proposal, not authorization or evidence of truth;
- no lease means no assumption of reserved capacity;
- stale attestation or expired lease blocks privileged execution;
- fallback cannot move restricted data to an unauthorized region or provider.

### 3.8 Evidence and formal verification records — W06

**SourceArtifact**: immutable source identity, publisher/issuer, acquisition method, URI/provider, acquired time, content digest, signature/transport evidence, rights/consent, classification and custody chain.

**SourceSpan**: artifact ID plus exact page/line/byte/time/media coordinates and extraction/transformation version.

**ClaimRecord**: claim ID/type, proposition, scope, jurisdiction, temporal validity, uncertainty semantics, epistemic class and status.

**EvidenceLink**: claim ID, source span, support/contradict/qualify relation, method, independence group, reviewer and limitations.

**ProofArtifact**: proposition, formal system/theory, assumptions, proof bytes/digest, checker identity/version, resource limits and reproducible verification result.

Rules:
- observation, report, inference, forecast, simulation, formal proof, decision and action receipt are distinct epistemic classes;
- evidence links do not automatically entail claims;
- signatures and repeated sources do not prove truth or independence;
- retraction, correction, expiry and supersession are first-class events;
- FRL accepts only proofs checked by a declared trusted checker under resource limits.

### 3.9 Simulation and Reality Bridge records — W07

**WorldManifest**: world ID/version, domain, units/coordinates/timebase, initial state, source datasets, model/kernel versions, trust zone and limitations.

**ExperimentSpec**: hypothesis, intervention, assumptions, control/baseline, variables, outcome metrics, random seeds, budget and stop conditions.

**SimulationRun**: world/experiment versions, fidelity tier, execution environment, inputs, outputs, uncertainty, calibration/holdout references, OOD status and reproducibility metadata.

**RealityBridgeApproval**: simulation evidence, domain safety review, human approval, real-world target, permitted action envelope, expiry and rollback/stop conditions.

Rules:
- simulated outcomes never become observed facts;
- fidelity tier and calibration must accompany every result;
- Reality Bridge cannot autonomously translate a simulation into real-world actuation;
- real-world action uses W01 authorization and W02/W05 dispatch contracts.

### 3.10 Surface and device records — W08

**SurfaceSession**: surface type/version, principal assertion, session ID, device/workload identity, channel, audience, capabilities, policy epoch and expiry.

**DeviceAttestation**: device identity, measured state, trust root, measurement version, nonce, freshness, revocation and verifier.

**MediaCustodyRecord**: media artifact, capture device/source, operator/consent, time/location precision, transformation lineage, rights, retention and integrity evidence.

**OfflineSnapshotLease**: snapshot ID, anchor/epoch, permitted offline actions, data scope, expiry, revocation freshness and reconnect policy.

Rules:
- every surface has an explicit capability manifest; UI visibility is not authority;
- browser isolation and egress must be enforced at the actual execution/network boundary;
- offline mode uses bounded, explicit permissions and must surface stale/revocation state;
- reconnect reconciles durable outbox/inbox, duplicate delivery, ordering, conflicts and uncertain external effects.

### 3.11 Security, release and operations records — W09/W11

**TrustBundle**: root/issuer hierarchy, signer roles, key IDs/epochs, revocation policy, trust-zone scope and rotation process.

**ReleaseEvidence**: source commit, dependency/SBOM, builder identity/environment, build provenance, artifact digest, signer, approval quorum, vulnerability policy, deployment measurement, staged promotion and rollback.

**IncidentRecord**: detection, scope, affected identities/keys/artifacts, containment authority, forensic evidence, recovery epoch, restore verification and closure approval.

Rules:
- key metadata is not proof of production KMS/HSM custody;
- artifact signature is not full build provenance;
- CI success is commit/job-specific and not operational readiness;
- recovery cannot silently lower trust policy or erase forensic evidence.

### 3.12 Domain, financial and public-impact records — W10/W12

**DomainQualification**: specialist/operator identity, issuer, credentials, scope, jurisdiction, standards/version, calibration, conflicts, expiry, revocation and escalation path.

**FinancialEntry**: ledger/account, debit/credit, currency, transaction ID, beneficiary, purpose, consent, authorization, settlement state, reconciliation and dispute/refund links.

**GovernanceDecision**: electorate/membership basis, quorum, conflict declarations, proposal, vote evidence, decision scope, appeal and expiry.

**ImpactEvidence**: baseline/counterfactual, boundary, geography/time, methodology, activity/output/outcome/net impact, uncertainty, leakage/rebound/permanence, independent verifier and correction path.

Rules:
- domain routing is not professional qualification;
- runtime authority never comes from marketplace reputation, payment, membership or community votes;
- financial ledger is double-entry, segregated and independently reconciled;
- environmental/community claims distinguish activity from independently measured net outcomes;
- restricted funds and personal contributions cannot be silently commingled.

## 4. Canonical handoff matrix

| Handoff | Producer → consumer | Required record | Blocking failure |
|---|---|---|---|
| Surface → ingress | W08 → W01 | SurfaceSession + PrincipalAssertion | unauthenticated, stale or wrong audience |
| Principal → planner | W01 → W02 | OperationEnvelope | missing principal, consent or purpose |
| Planner → agent fabric | W02 → W04 | ExecutionEnvelope + StepInvocation | broken DAG, missing lineage or budget |
| Agent → capability broker | W04 → W01/W05 | DelegationLease + ActionIntent | unqualified agent, expired lease or scope mismatch |
| Capability broker → executor | W01/W09 → W02/W05 | AuthorizationReceipt | deny, replay, stale epoch or target mismatch |
| Executor → provider | W02/W05 → provider | DispatchAttempt | no idempotency policy or placement lease |
| Provider → effect reconciler | provider → W05/W03 | EffectReceipt | unauthenticated/ambiguous result; preserve UNKNOWN |
| Result → verifier | W04/W05 → W06/W02 | AgentResult + EvidenceLink | missing provenance or task coverage |
| Verifier → state | W06/W02 → W03 | ResultAdmission + StateCommit | unaccepted/indeterminate result |
| State → memory/audit | W03 → W03/W09 | MemoryRecord + AuditEvent | scope, retention or integrity failure |
| Research → NEXUS | W06 acquisition → claim graph | SourceArtifact + SourceSpan + ClaimRecord | missing custody/span/epistemic type |
| Simulation → Reality Bridge | W07 → W01/W02/W10 | SimulationRun + approval | uncalibrated, OOD, unauthorized or no human review |
| Device/offline → sync | W08 → W01/W03/W09 | OfflineSnapshotLease + durable receipts | stale epoch, replay, conflict or uncertain effect |
| Specialist → decision | W10 → W02/W12 | DomainQualification + assessment | out of scope, expired credential or missing review |
| Financial action → ledger | W12 payment adapter → ledger | FinancialEntry + settlement receipt | no consent, segregated custody or reconciliation |
| Impact report → public claim | W12 → W06/W10 | ImpactEvidence | no baseline, independence or uncertainty |
| Build → release | W09/W11 pipeline → deployment | ReleaseEvidence | missing builder/approval/deployment proof |
| Incident → recovery | W09/W11 → W01/W03 | IncidentRecord + RecoveryAuthorization | untrusted restore, stale epoch or absent approval |

## 5. Shared lifecycle vocabulary

The following are distinct axes; do not force them into one overloaded status enum.

**Request/operation:** RECEIVED → AUTHENTICATED → ACCEPTED → PLANNED → COMPLETED / PARTIAL / REJECTED / CANCELLED / FAILED.

**Execution:** CREATED → VALIDATED → READY → RUNNING → RESULT_ADMITTED → STATE_COMMITTED, with BLOCKED / PARTIAL / CANCELLED / FAILED / INDETERMINATE.

**External effect:** NOT_DISPATCHED → DISPATCH_INTENT_DURABLE → DISPATCHED_OR_POSSIBLE → CONFIRMED / REJECTED / UNKNOWN → RECONCILED / COMPENSATED.

**Evidence:** ACQUIRED → CUSTODY_VALIDATED → EXTRACTED → LINKED_TO_CLAIM → REVIEWED → ACCEPTED_FOR_SCOPE / DISPUTED / RETRACTED / EXPIRED.

**Qualification:** PROPOSED → ISSUER_VERIFIED → SCOPE_REVIEWED → ACTIVE → SUSPENDED / EXPIRED / REVOKED.

**Placement lease:** REQUESTED → ADMITTED → RESERVED → ACTIVE → RELEASED / EXPIRED / FENCED.

**Release:** BUILT → PROVENANCE_VERIFIED → APPROVED → STAGED → DEPLOYED → MONITORED → PROMOTED / ROLLED_BACK / REVOKED.

## 6. Failure and retry matrix

| Failure | Required result | Retry rule |
|---|---|---|
| Principal invalid/expired/revoked | DENIED; no privileged work | re-authenticate; never reuse stale assertion |
| Capability denied/replay/stale epoch | REJECTED; audit decision | no automatic retry without new decision/nonce |
| Agent unavailable/lease expired | BLOCKED or PARTIAL | reselect only with new valid lease and preserved lineage |
| Provider fails before dispatch | NOT_DISPATCHED | bounded retry under same operation, new attempt |
| Provider timeout after dispatch | EFFECT_UNKNOWN | query target/reconcile; do not blind retry |
| Result schema invalid | RESULT_REJECTED | bounded repair/replan; preserve invalid artifact |
| Semantic evidence insufficient | INDETERMINATE | seek independent evidence/reviewer; no forced pass |
| Journal unavailable | COMMIT_UNAVAILABLE | do not claim durable success; use declared safe outbox only |
| Memory unavailable | CONTEXT_UNAVAILABLE/PARTIAL | do not silently treat as empty |
| Revocation state stale offline | RESTRICTED_OFFLINE | only explicitly permitted low-risk actions |
| Placement capacity lost | LEASE_FENCED/BLOCKED | reacquire; never assume previous capacity |
| Simulation OOD/un-calibrated | SIMULATION_INDETERMINATE | no Reality Bridge approval |
| Domain qualification expired | DOMAIN_REVIEW_REQUIRED | no specialist conclusion beyond safe scope |
| Ledger settlement mismatch | RECONCILIATION_HOLD | freeze affected funds path; independent reconciliation |
| Impact evidence disputed | CLAIM_DISPUTED | preserve source and correction trail |
| Release provenance incomplete | RELEASE_BLOCKED | no promotion; rebuild/re-attest |

## 7. Versioning and compatibility

- Each schema has one canonical owner and a published schema registry entry.
- Major version changes alter meaning or required fields; explicit migration is mandatory.
- Minor versions add optional fields only if old consumers can safely ignore them.
- Patch versions correct clarifications without semantic change.
- Unknown critical fields fail closed; unknown optional fields are preserved when round-tripping.
- Adapters are named, versioned, observable and tested for loss; no silent field dropping.
- Schema deprecation has announced date, consumer inventory, migration path and removal evidence.
- Event records retain the schema version used at creation; never rewrite old evidence into a new schema without a linked transformation record.
- Canonical IDs are opaque, globally unique within declared issuer namespace, and never reused after deletion/revocation.
- Time values include clock source, precision and skew bounds; monotonic sequence is separate from wall-clock time.

## 8. Ownership and decision authority

| Contract family | Accountable architectural owner | Writers/producers | Consumers | Decision authority boundary |
|---|---|---|---|---|
| Principal/delegation/capability | W01 | identity issuer, policy evaluator | all privileged surfaces/executors | only W01 policy issuer grants capability |
| Operation/execution lifecycle | W02 | coordinator/runtime | agents, tools, providers, journals | coordinator owns execution identity/state |
| Durable state/recovery/memory | W03 | journal/state/memory adapters | runtime, evidence, audit | state authority owns commits; memory cannot authorize |
| Agent qualification/delegation | W04 | registry/qualification issuer | scheduler/coordinator | qualification does not grant capability |
| Provider/resource dispatch | W05 | router/provider/placement scheduler | runtime/effect reconciler | provider response cannot self-verify effect |
| Evidence/claims/formal proof | W06 | acquisition/evaluator/checker | all domain and simulation consumers | evidence verifier admits claims for scope |
| Simulation/world | W07 | world model/kernel/experiment runner | research, domain, Reality Bridge | simulation cannot authorize real-world action |
| Surfaces/device/offline | W08 | surface adapters/device issuer | ingress/runtime/sync | UI cannot widen authority |
| Security/release/audit | W09 | key, audit, build/release and incident services | all planes | security may deny; audit does not authorize |
| Domain specialists | W10 | qualified specialist/reviewer | cognition, user and action planner | scoped specialist authority only |
| Global operations | W11 | scheduler, node control, SRE | all distributed services | capacity admission cannot override policy |
| Economy/governance/impact | W12 | ledger, payment, community and impact services | user/business/public reporting | no ledger/reputation/governance authority over runtime |

Where multiple planes share a decision, one accountable owner is designated and other planes are consulted; there are no co-equal implicit issuers.

## 9. Traceability and change invalidation

Each contract implementation/evidence card must include:
- canonical contract ID and version;
- owner and decision/ADR reference;
- exact source path and blob SHA;
- constructors, registrations, entrypoints, callers, readers and writers;
- issuer and consumer identities;
- persistence and external side-effect map;
- error/retry/cancel/expiry/recovery/deletion semantics;
- tests/evidence and exact commit/configuration;
- known uninspected paths and residual uncertainty.

A change to a source blob invalidates only the evidence cards that depend on that blob and its transitive contract dependencies. The dependency graph must identify affected streams; unrelated evidence is not automatically invalidated. Re-run discovery for affected constructors/callers before updating a closure status.

## 10. Acceptance checklist for every handoff

A handoff is not architecturally closed until:
- [ ] schema and version are canonical and owned;
- [ ] issuer, audience, principal, tenant and authority are explicit;
- [ ] producer and every consumer/call site are inventoried;
- [ ] identifiers preserve parent/child/attempt lineage;
- [ ] persistence, retention, deletion and recovery are explicit;
- [ ] success, denial, partial, timeout, stale, unavailable and unknown outcomes are explicit;
- [ ] retry/idempotency/compensation are defined for external effects;
- [ ] provenance, uncertainty and independent review are explicit;
- [ ] privacy, residency, safety and abuse boundaries are explicit;
- [ ] resource limits, observability and degraded mode are explicit;
- [ ] migration/deprecation and rollback are explicit;
- [ ] later acceptance evidence is observable and tied to a named environment.

## 11. Parallel closure assignments after this catalog

- **W01/W02/W08:** complete entrypoint-by-entrypoint principal and execution-envelope adoption map, including direct API routes, Gateway, CLI and JARVIS.
- **W02/W03/W05/W09:** enumerate all dispatch and retry paths; identify the one retry/effect coordinator and journal reservation owner.
- **W03/W06/W09/W12:** enumerate all stores and ledgers; classify custody, retention, deletion, backup and independent reconciliation.
- **W04/W05/W10/W11:** complete agent qualification, provider/model routing, placement leases and capacity ownership.
- **W06/W07/W10:** complete epistemic object schemas, proof checker trust, simulation fidelity and domain qualification.
- **W08/W09/W11:** complete actual enforcement inventory for browser, device, offline, network egress, key custody and deployment.
- **W12:** separate executable capabilities from roadmap; specify accounting invariants, governance safeguards and impact measurement.
- **Cross-stream:** run schema/ADR/identifier consistency audit; resolve only with evidence and recorded owner decisions.

## 12. Disposition

This catalog is a normative convergence proposal, not an accepted ADR, implemented schema registry or architecture freeze. It does not claim that any listed object currently exists as a production type. It creates no duplicate canonical plane enum and does not authorize integration or tests.

**W01–W12 remain PARTIAL.**
