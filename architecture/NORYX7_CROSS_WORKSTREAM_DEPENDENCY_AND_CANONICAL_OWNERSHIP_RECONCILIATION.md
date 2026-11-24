# NORYX7 — Cross-Workstream Dependency, Canonical Ownership and End-to-End Lifecycle Reconciliation

**Review date:** 2026-11-25  
**Parent:** System-Wide Architecture Closure / PR #212  
**Scope:** architecture-only synthesis across W01–W12 and P01–P18.  
**Source baseline reviewed:** `acda1ba43924af41c26f0662a6dcdf638c54ac26`  
**Status:** proposed reconciliation; no architecture freeze, implementation, integration or verification claim.

## 1. Purpose and boundary

This document closes a missing system-level view: the workstreams have individual scopes and source-reconciliation notes, but their dependencies, ownership handoffs and end-to-end lifecycle must be read as one graph.

It does not create another canonical plane enum, runtime, identity authority, state store, agent fabric, router, evidence format, security gate or ledger. It binds existing architecture decisions and open questions into one dependency and responsibility model. Existing ADRs and subsystem documents remain authoritative for their detailed subject matter.

The workstreams remain concurrent for discovery and design. Dependency edges constrain contract acceptance and freeze order; they do not prevent downstream streams from discovering requirements or documenting blockers.

## 2. System invariants

1. One principal/identity model binds humans, services, agents, devices, workloads and tenants; credentials and local caches are evidence or projections, not competing identity authorities.
2. One canonical policy/capability decision path authorizes privileged actions. Surfaces, agents, domain packages, schedulers, marketplaces and adapters cannot mint or widen authority.
3. One logical runtime coordination model owns lifecycle and dispatch admission. Existing runtimes may remain distinct processes or adapters only where their responsibilities and boundaries are explicit.
4. One logical state/journal contract governs trusted commits, idempotency, replay, version conflicts and recovery. Specialized stores may exist behind typed namespaces and ownership rules.
5. Every externally consequential action has a bound principal, scoped capability, policy epoch, approval when required, idempotency key, bounded execution lease and auditable outcome.
6. An agent result, model response, simulation output, heuristic score, formal proof and independently measured real-world outcome are different epistemic objects.
7. Only evidence admitted under a declared claim, provenance, validity, independence and review policy can support a trusted conclusion; output presence is not semantic verification.
8. Distribution transports state and work but cannot broaden authority, erase provenance, bypass revocation or silently resolve conflicting state.
9. A simulation-to-reality transition is a separate policy-controlled operation, never an implicit side effect of a successful simulation.
10. Financial, marketplace, contributor and environmental records are not identity, policy, authorization or runtime state authorities.
11. Recovery, revocation, emergency stop and containment outrank ordinary execution and resource priority.
12. Architecture status, implementation status and verification status remain independent axes.

## 3. Canonical responsibility map

The following are logical ownership assignments, not claims that one current source file already implements each responsibility completely.

| Responsibility | Canonical logical owner | Must not become an alternate owner |
|---|---|---|
| Principal identity, enrollment, binding and session | W01 identity/trust authority | JARVIS, Browser, agent registry, tenant billing, local device cache |
| Policy evaluation, capability issuance and revocation | W01 policy/capability authority | Domain specialist, planner, scheduler, tool adapter, marketplace |
| Request lifecycle and orchestration | W02 canonical runtime coordinator | Parallel facade with independent lifecycle or hidden dispatch |
| Trusted state commit, journal and recovery epoch | W03 state/journal authority | Memory replica, telemetry store, domain database, UI cache |
| Agent registration, delegation, supervision and result admission | W04 agent fabric under W01 grants and W02 lifecycle | Provider router, specialist catalog, collaboration helper |
| Model/provider selection | W05 provider-routing responsibility | Agent allocator or node placement |
| Agent/task allocation | W05 agent-allocation responsibility | Provider/model router |
| Scheduling, placement, dispatch and budgets | W05 scheduler/resource-placement responsibility | Provider selection, domain package, surface |
| Semantic types, claims, provenance and evidence identity | W06 shared semantic/evidence substrate | Each domain's private claim format or audit log |
| Simulation world/scenario and fidelity | W07 MIRROR WORLD | Real-world observation store or cyber-range completion flag |
| Browser/JARVIS/terminal/device ingress and presentation | W08 surface adapters | Surface-local policy or durable global identity |
| Cryptographic controls, security posture and assurance | W09 security architecture; enforcement remains in canonical W01/W02/W03 paths | Second authorization broker or independent runtime gate |
| Domain methods, specialist qualification and escalation | W10 domain packages | Global orchestrator, authority broker, evidence issuer |
| SLOs, telemetry, incident and continuity operations | W11 operational control plane | Business ledger or agent self-report alone |
| Product, marketplace, funds and community governance | W12 ecosystem governance and ledgers | Runtime state, identity authority, policy or audit truth |

### 3.1 Canonical planes

All responsibility mappings must use the existing P01–P18 enum and its current ordering. Cross-cutting concerns (NEXUS, FRL, MIRROR WORLD, privacy, human control, domain assurance and ecosystem governance) map onto existing planes; they do not create additional canonical planes. Any change to the enum requires an explicit amendment to ADR-001 and a full compatibility analysis.

### 3.2 Authority is not the same as ownership

A component may own a schema, lifecycle or domain record without having authority to approve an action. For example:
- W10 owns domain-specific assessment rules but cannot grant an agent permission to execute.
- W05 owns scheduling and resource placement but cannot relax policy or revocation.
- W08 owns user interaction and consent capture presentation but cannot self-assert durable consent outside the canonical identity/policy record.
- W12 owns financial and community governance records but cannot authorize access to NORYX7 runtime resources.
- W11 owns operational incident procedures but privileged containment actions still require the defined emergency authority and audit path.

## 4. Cross-workstream dependency graph

### 4.1 Contract-acceptance dependencies

| Workstream | Upstream contracts required before its contract can freeze | Downstream consumers |
|---|---|---|
| W01 Identity, trust, authority | None; foundational | W02–W12 |
| W02 Runtime topology | W01 | W03–W12 |
| W03 State, data, recovery | W01, W02 | W04–W12 |
| W04 Agent fabric | W01, W02, W03 | W05–W12 |
| W05 Routing, scheduling, resources | W01, W02, W04 | W07, W08, W10, W11, W12 |
| W06 Semantics, knowledge, evidence | W01, W03; discovery may proceed earlier | W07, W09, W10, W11, W12 |
| W07 MIRROR WORLD | W01, W03, W06 | W09, W10, W11, W12 |
| W08 Surfaces and distribution | W01, W02, W05, W06 | W09, W10, W11, W12 |
| W09 Security and assurance | W01, W02, W03, W06 | W07, W08, W10, W11, W12 |
| W10 Domain fabrics | W01, W03, W06, W09 | W07, W08, W11, W12 |
| W11 Performance and operations | W01–W09 contracts relevant to each operational path | W10, W12 and all production-facing paths |
| W12 Product and ecosystem | W01, W03, W05, W06, W08, W09, W11 | Product/domain deployments and community programs |

A dependency means “cannot freeze the dependent contract while the upstream meaning is unresolved”; it does not mean the downstream stream must stop discovery. W06 and W09 must continue in parallel with W01–W05 while recording provisional assumptions and explicit blockers.

### 4.2 Critical path and parallel lanes

**Critical trust/state lane:** W01 → W02 → W03 → W04 → W05.  
**Shared meaning lane:** W01/W03 → W06, then W06 joins W07/W09/W10.  
**Execution-surface lane:** W01/W02/W05/W06 → W08.  
**Assurance lane:** W01/W02/W03/W06 → W09 → W10/W11.  
**Ecosystem lane:** W01/W03/W05/W06/W08/W09/W11 → W12.

These lanes are a dependency view, not a waterfall. Source inventory, gap discovery, threat modeling, domain research and failure analysis continue concurrently across all twelve streams.

## 5. End-to-end lifecycle and handoff contracts

### 5.1 Ingress and intent

**Sequence:** surface receives input → preserve source artifact and user gesture/consent context → bind request to principal, tenant and session → classify data and requested effects → create immutable request/correlation identity.

W08 owns the surface adapter. W01 owns principal/session binding and policy meaning. W06 owns shared semantic representation and provenance references. No surface may create a privileged capability by interpreting a user phrase or by carrying a stale UI flag.

Required contract fields: request ID, principal ID, tenant/scope, session binding, source surface, original artifact reference, capture time, consent/gesture reference where applicable, data classification, schema version, expiry and correlation/trace ID.

### 5.2 Planning and decomposition

**Sequence:** canonical runtime accepts the request → policy classifies permitted planning scope → cognition decomposes the task → plan references required evidence, agents, tools, resources and risk → independent policy/capability check before dispatch.

W02 owns lifecycle; W04 owns agent/task contracts; W05 owns resource feasibility. Planning is not authorization. A plan can be valid yet non-executable. Plan mutation after approval invalidates the approval digest and requires re-evaluation.

### 5.3 Agent and provider dispatch

W04 resolves agent identity, qualification status, delegation chain, lease, supervision and result contract. W05 separately resolves model/provider, resource tier, schedule, placement, budget and transport. A provider is not an agent identity; an agent identity is not a provider; a selected compute tier is not permission.

Every dispatch must bind:
- originating request and plan digest;
- principal and delegated agent identity;
- capability scope and policy epoch;
- task and tool allow-list;
- provider/model version and declared data handling;
- node/region/placement constraints;
- resource/time/token/storage/cost budgets;
- idempotency and cancellation identifiers;
- lease expiry and result-admission requirements.

Retry/failover must preserve idempotency and must not duplicate uncertain external effects.

### 5.4 Evidence, reasoning and specialist assessment

W06 defines canonical claim, source, evidence, provenance, temporal validity, contradiction and epistemic-state references. W10 defines domain method, qualification, jurisdiction, specialist scope, calibration, escalation and review. W07 supplies simulation evidence with explicit synthetic-world identity and fidelity limitations. W09 supplies assurance evidence about integrity, authorization and threat conditions.

A specialist conclusion must identify whether it is heuristic, model assessment, calibrated forecast, formal proof under assumptions, simulation result or independently measured outcome. These types cannot be silently promoted into one another.

Independent corroboration requires analysis of shared model family, provider, corpus, retrieval path, prompt, toolchain, operator and failure domain. Different agent IDs alone are insufficient.

### 5.5 Verification and result admission

Result admission is distinct from checking that output exists. The admission contract validates:
1. task, request, agent, delegation and execution identity;
2. schema and version compatibility;
3. provenance references and source integrity state;
4. required evidence coverage and freshness;
5. domain scope, jurisdiction, qualification and uncertainty;
6. contradiction and independence requirements;
7. budget and policy compliance;
8. verifier identity, authority and independence;
9. explicit outcome state and reason codes.

Allowed outcomes include accepted-for-scope, rejected, incomplete, indeterminate, unsupported, degraded, failed, quarantined and expired. “Accepted-for-scope” means only that the declared admission criteria passed; it is not universal truth.

### 5.6 Commit, memory and audit

W03 owns the trusted state/journal contract and commit outcome. W06 owns semantic references and provenance; W11 owns diagnostic telemetry and operational events; W12 owns separate financial/community ledgers. The records may reference one another by stable IDs and signed digests but must not be conflated or share write authority.

Commit requires an admitted result, matching state version, valid authorization epoch, idempotency decision and audit availability. Uncertain external side effects enter reconciliation, not blind retry. Memory is a projection or domain-specific persistence under explicit retention/deletion rules; it is not a second state authority.

### 5.7 External action and Reality Bridge

Before any external action, re-check principal, capability, target, operation, policy epoch, lease, consent, approval digest, safety envelope and resource budget. W07 simulation success never authorizes a real-world operation. A Reality Bridge request is a new action with a new target-specific authorization, independent safety review where required, rollback/containment plan and immutable audit record.

### 5.8 Distribution, synchronization and offline operation

W08 transports requests and data; W05 places work; W03 governs state convergence and commit; W01 governs identity and revocation; W09 defines cryptographic and trust controls; W11 defines degraded operation and recovery. A disconnected node may perform only explicitly declared offline-safe actions under bounded revocation freshness. Conflicts remain explicit; last-write-wins is not a universal trust policy.

### 5.9 Incident, recovery and continuity

W11 detects and coordinates incident response. W09 supplies security classification, evidence preservation and key/trust procedures. W01 revokes principals/capabilities. W02 stops or drains execution. W03 restores trusted state under a new recovery epoch. W05 reallocates resources only after policy permits. W12 reconciles business/community consequences without overriding technical trust decisions.

Canonical sequence: DETECT → CLASSIFY → CONTAIN → REVOKE → PRESERVE → RESTORE → RE-ATTEST → RECONCILE → MONITOR. Each transition must have an owner, preconditions, evidence, timeout, failure outcome and audit event.

### 5.10 Product, financial and community lifecycle

W12 may onboard tenants, projects, contributors, merchants and community initiatives, but identities must bind to W01 and financial records must remain in separate ledgers with double-entry accounting, segregation of duties, approvals, reconciliation, dispute/chargeback and audit controls. Marketplace ratings, donations, contribution hours and impact claims are not evidence of professional qualification or authorization.

Environmental and public-impact claims require a baseline, methodology, boundary, measurement interval, independent measurement where material, uncertainty, attribution and safeguards against double counting. Distinguish activity performed, output delivered, outcome observed and impact causally supported.

## 6. Cross-cutting contract registry

| Contract family | Canonical owner | Required shared fields/semantics | Primary consumers |
|---|---|---|---|
| Identity and delegation | W01 | principal, issuer, subject, scope, epoch, expiry, revocation, chain | W02–W12 |
| Request/plan/execution | W02 | request ID, plan digest, lifecycle state, cancellation, deadline | W03–W12 |
| State/commit/recovery | W03 | namespace, version, idempotency, journal sequence, epoch, outcome | W04–W12 |
| Agent/result | W04 | agent ID, qualification ref, lease, delegation, task, result state | W05–W12 |
| Routing/resource | W05 | provider, model, tier, node, region, budget, reservation, dispatch | W07–W12 |
| Semantic/evidence | W06 | claim, source artifact, exact locator, provenance, validity, epistemic type | W07–W12 |
| World/experiment | W07 | world ID, scenario, model/version, fidelity, isolation, bridge authorization | W09–W12 |
| Surface/session | W08 | origin, gesture/consent, capture, data exposure, local/remote boundary | W09–W12 |
| Security/assurance | W09 | threat, control, key/attestation refs, authorization evidence, incident state | W01–W12 |
| Domain qualification | W10 | domain, jurisdiction, competence evidence, method, calibration, reviewer | W06–W12 |
| Operations/continuity | W11 | SLO, telemetry class, incident, runbook, recovery epoch, capacity | W01–W12 |
| Ecosystem/ledger | W12 | tenant, project, transaction, fund restriction, governance, impact measurement | W08–W11 |

All contracts require schema version, canonicalization rules, compatibility class, provenance, owner, retention/deletion policy, failure semantics and testable acceptance criteria. No consumer may reinterpret an upstream field in a way that widens privilege.

## 7. Shared failure and uncertainty semantics

A single result vocabulary must distinguish at least: accepted, rejected, incomplete, indeterminate, unsupported, degraded, failed, quarantined and expired. Add explicit reason codes for authorization, stale epoch, schema mismatch, evidence absence, source contradiction, reviewer conflict, budget exhaustion, timeout-before-effect, uncertain-effect, version conflict, partition and recovery-in-progress.

The following transitions are forbidden:
- missing evidence → accepted;
- verifier exception → accepted;
- model confidence → calibrated probability without calibration evidence;
- simulation verified → real-world verified;
- agent identity diversity → independent corroboration;
- timeout with uncertain side effect → automatic retry;
- stale offline revocation → privileged execution;
- marketplace or financial record → authorization;
- environmental activity count → causal impact claim.

## 8. Cross-stream collision and overlap register

| Collision risk | Canonical resolution rule | Evidence still required |
|---|---|---|
| Multiple runtime classes/coordinators | One logical lifecycle owner; other runtimes become bounded engines/adapters or explicitly separate services | Constructor/call-site graph, startup/shutdown paths, JARVIS and gateway bridge mapping |
| Multiple identity registries | One durable principal/binding authority; local registries are caches/projections with freshness and revocation contract | Persistence, bootstrap, migration, offline and recovery evidence |
| Multiple capability/action gates | One canonical issuance/evaluation path; enforcement points consume signed/scoped decisions | Full call graph, issuer uniqueness, replay and revocation proof |
| Multiple state stores/journals | One logical commit protocol; domain stores have explicit namespaces and transaction/saga semantics | All writers/readers, journal ordering, external witness, restore and uncertain side-effect handling |
| Agent and provider routing overlap | W04 chooses qualified agent; W05 selects provider and placement under budgets | Dispatch call graph and failover/retry composition |
| Memory and state overlap | Memory is a managed data class/projection; trusted commit remains W03 | Read/write map, deletion, replica tombstones and recovery behavior |
| Audit, telemetry and business ledger overlap | Separate event classes, owners, retention, access and integrity policies | Event schema inventory, signing, retention and reconciliation |
| Domain-specific evidence formats | Shared W06 claim/evidence envelope; domain-specific payloads are typed extensions | Schema compatibility, exact source locators, calibration and reviewer semantics |
| Cyber-range and MIRROR WORLD overlap | Cyber-range is one bounded synthetic environment; W07 owns world/scenario/fidelity lifecycle | Simulator inventory, isolation and Reality Bridge boundaries |
| Offline and distributed trust overlap | W01 revocation + W03 state epochs + W09 crypto; W08 transports; W11 governs degraded mode | Anchor/issuer, freshness limits, conflict resolver and restore tests (later phase) |
| Marketplace/community and runtime authority | W12 ledgers and governance never issue runtime capabilities | Tenant mapping, funds segregation, dispute and audit model |

This register records collision hypotheses and the required proof. It does not declare any source-level collision resolved merely by naming a canonical owner.

## 9. Required source evidence before contract freeze

For each ownership row and dependency edge, collect:
- exact source paths and commit SHA;
- every constructor, registration, entrypoint, caller and mutation path;
- persistent stores, caches, journals, replicas and external side effects;
- API/schema versions and compatibility behavior;
- principal and capability issuers/consumers;
- lifecycle states, cancellation, expiry, retries and recovery;
- failure injection points and fail-closed behavior;
- observability/audit events and sensitive-data boundaries;
- resource, time, cost, fan-out and storage bounds;
- tests or independent evidence that would later validate each claim.

Repository-wide searches and inventories are discovery aids, not proof that every dynamic import, plugin, external deployment or runtime call path has been found. Mark scope and residual uncertainty explicitly.

## 10. Architecture closure acceptance matrix

A workstream may be marked **ARCHITECTED** only when all applicable items are complete:

- [ ] Scope, non-goals and canonical plane mapping are explicit.
- [ ] Source inventory and exact source revision are recorded.
- [ ] Every component has one primary lifecycle owner.
- [ ] Producers, consumers, schemas and version rules are mapped.
- [ ] Authority, identity, delegation and revocation are explicit.
- [ ] State ownership, persistence, retention, deletion and recovery are explicit.
- [ ] Cross-stream dependencies and collision risks are resolved or assigned.
- [ ] Success, partial, failure, timeout, cancellation, expiry and uncertain-effect paths are defined.
- [ ] Security, privacy, abuse, safety and human-control requirements are explicit.
- [ ] Evidence, provenance, uncertainty and reviewer independence are explicit.
- [ ] Resource limits, SLO boundaries and degraded modes are explicit.
- [ ] Migration, compatibility, rollback and deprecation are specified.
- [ ] Open decisions have an owner, priority, rationale and exit criterion.
- [ ] Acceptance criteria are observable and do not confuse architecture with implementation verification.

**ARCHITECTURE-FROZEN** additionally requires all blocking decisions resolved, all high-priority decisions resolved or explicitly dispositioned under the governing freeze policy, no unresolved authority/state/schema conflict, and explicit review approval. A checklist or document count alone cannot satisfy this gate.

Implementation and verification remain separate axes. No source code, tests, dependencies, workflows, deployment or runtime behavior are changed or certified by this document.

## 11. Next discovery passes by lane

All lanes continue concurrently:

- **W01–W03:** trace every identity issuer, policy evaluator, capability broker, runtime entrypoint, state writer, journal and recovery consumer; resolve canonical ownership with source call graphs.
- **W04–W05:** trace all agent registration/dispatch/result paths and separate provider routing, agent allocation, scheduling, placement, retries and budgets.
- **W06–W07:** define claim/evidence/semantic schemas and world/scenario/experiment/fidelity contracts; bind simulation outputs to explicit epistemic types.
- **W08:** map every browser, JARVIS, terminal, API, mobile, edge/cloud and offline ingress path to the same identity/session/authority lifecycle.
- **W09–W11:** reconcile key custody, attestation, audit, secure update, supply chain, observability, SLOs, incident and recovery across all runtimes and nodes.
- **W10–W12:** complete specialist qualification and jurisdiction model, scientific calibration, financial segregation, marketplace governance, community safeguards and independently measured environmental impact.
- **All streams:** inspect cross-cutting data classes, privacy/retention, multimodal source locators, accessibility, localization, abuse cases, resource budgets and supply-chain provenance.

## 12. Decision disposition

This is a system-level synthesis and proposed ownership/dependency contract. It consolidates existing directions without superseding ADR-001 through ADR-005 or creating a duplicate decision series. Any unresolved choice that changes an existing ADR must be recorded in that ADR/backlog with alternatives, consequences and migration impact.

**Current status remains: W01–W12 PARTIAL; architecture not frozen.**
