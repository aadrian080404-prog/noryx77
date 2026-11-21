# NORYX7 — Canonical Plane Contract Cards

**Status:** architecture-only contract specification; not implementation or verification evidence  
**Authority source:** `core/architecture_gate.py` and `core/architecture_registry.py`  
**Important correction:** the executable enum defines **19 canonical planes**. Earlier system-wide summary material described 18; this document corrects the count. The canonical names and ordering below follow the executable enum.

## 0. Contract model

Each plane contract defines: purpose; authoritative inputs/outputs; owner; trust and authority boundary; state/lifecycle; failure semantics; resource envelope; observability; recovery; dependencies; compatibility; and future acceptance evidence. These are architecture declarations. Existing files are evidence of an implementation location, not proof that the full contract is implemented.

Common invariants:
- authenticated identity and execution scope travel with privileged work;
- policy and capabilities, not models or semantic documents, authorize actions;
- data and results retain provenance and validity intervals;
- all operations are bounded by time, memory, size, concurrency and cancellation;
- unknown, malformed, stale, revoked or over-budget privileged operations fail closed;
- state mutation is separated from proposal, execution and verification;
- every component declares its degraded and recovery behavior.

## P01 — Ingress

**Purpose:** accept bounded requests/events from user surfaces, APIs, devices and trusted internal producers.

- Inputs: source envelope, principal/session reference, modality, content reference, timestamp, request metadata.
- Outputs: normalized immutable ingress record, validation outcome, correlation identifiers.
- Owner: ingress contract layer; current anchors include `core/contracts.py`, `core/limits.py`, identity and platform adapters.
- Authority: ingress authenticates/validates identity evidence but does not grant action capabilities.
- State: request lifecycle begins at received; validated; rejected; expired; cancelled.
- Failure: malformed schema, oversized payload, invalid encoding, identity mismatch, replay or unavailable parser → reject/quarantine; never infer missing privileged fields.
- Budgets: payload bytes, nesting, modality duration, rate, parser time, attachments and concurrent requests.
- Observability: source, schema version, request/correlation IDs, rejection reason, size and timing; avoid logging raw sensitive content.
- Recovery: retry only with idempotency key and freshness checks; expired requests require resubmission.
- Dependencies: Identity, Limits, User Understanding, NEXUS adapters, Audit.
- Acceptance: malformed/oversized/replayed requests rejected; normalization preserves source references; identity and tenant context cannot be swapped.

## P02 — Understanding

**Purpose:** derive bounded interaction/task signals and consent-aware context without creating authority.

- Inputs: user-provided request, explicit consent state, bounded profile signals, interaction session.
- Outputs: task interpretation candidates, context metadata, uncertainty and provenance references.
- Owner: `core/user_understanding.py`, `core/interaction_context.py`, JARVIS interaction context.
- Authority: no authentication, authorization, policy mutation or privilege influence.
- State: transient analysis; optional consented profile update; expiry/deletion states.
- Failure: absent/ambiguous consent or prohibited inference → deny processing or omit signal; conflicting signals remain unresolved.
- Budgets: content count/size, signal count, profile size, retention and compute.
- Observability: consent decision, transformations, provenance IDs, expiry; raw content excluded from profile/audit by default.
- Recovery: discard transient content; restore only validated profile snapshots; support correction and deletion propagation.
- Dependencies: Ingress, Privacy, Memory, NEXUS, Audit, Interfaces.
- Acceptance: consent isolation, data minimization, sensitive inference exclusion and no path from profile to authorization.

## P03 — Cognition

**Purpose:** coordinate bounded HYPERSYNTH cognitive stages and independent reasoning paths.

- Inputs: validated task/context/evidence references, risk class, resource budget, policy snapshot.
- Outputs: hypotheses, candidate plans, simulation requests, analysis and bounded recommendations.
- Owner: `core/hypersynth.py`, `core/reasoning.py`, `core/metacognition.py`, runtime bridge.
- Authority: cognitive agents propose only; no direct state commit or capability issuance.
- State: task-scoped cognitive run with immutable stage/evidence lineage.
- Failure: stage exception, missing evidence, budget exhaustion, disagreement or verifier failure → incomplete/indeterminate/failed; no automatic acceptance.
- Budgets: depth, branch count, tokens/compute, agents, wall time, context size and retries.
- Observability: stage transitions, agent identities, hypothesis/evidence references, budget consumption and challenge outcome.
- Recovery: cancel run, preserve partial artifacts as explicitly incomplete, resume only from integrity-checked checkpoints.
- Dependencies: Understanding, Planning, Routing, Agents, Memory, NEXUS, Mirror World, Verification, Audit.
- Acceptance: phase order and bounds; dissent retained; consensus never substitutes for independent verification.

## P04 — Planning

**Purpose:** convert objectives into bounded dependency-aware plans.

- Inputs: objective, constraints, task context, available capabilities (descriptive only), resource envelope.
- Outputs: immutable plan DAG, step contracts, preconditions, dependencies, stop and compensation conditions.
- Owner: `core/planning.py`, `core/decomposition.py`, JARVIS decomposition.
- Authority: plan content cannot grant itself authority or bypass ActionGate.
- State: draft → validated → authorized-for-dispatch reference → executing → completed/failed/cancelled.
- Failure: cycles, missing dependencies, unsupported step, invalid target, unbounded fan-out → reject plan.
- Budgets: node/edge count, depth, fan-out, duration, retry count and plan bytes.
- Observability: plan version/digest, dependency decisions, validation findings and replans.
- Recovery: immutable revisions; supersede rather than mutate active plans; cancellation propagates to descendants.
- Dependencies: Cognition, Capabilities, Tools, Routing, Runtime, Audit.
- Acceptance: DAG validity, deterministic ordering where required, correct dependency cancellation and no implicit privilege.

## P05 — Routing

**Purpose:** choose model, agent, tool, node and execution placement under policy/resource constraints.

- Inputs: validated task requirements, trust posture, capability availability, latency/privacy/residency and budget constraints.
- Outputs: route proposal with target identity, rationale, resource estimate and expiry.
- Owner: `core/router.py`, `core/resource_router.py`, provider routing and ecosystem placement.
- Authority: route selection does not grant capabilities; target authorization occurs independently.
- State: candidate → admitted → dispatched → completed/expired/revoked.
- Failure: no eligible route, stale attestation, partition or resource exhaustion → reject or explicitly degraded route.
- Budgets: candidate count, route time, queue depth, concurrency, resource and egress quotas.
- Observability: candidate set, exclusion reasons, selected target, trust evidence and route latency.
- Recovery: failover only to independently trusted targets; preserve execution binding; no silent cloud fallback from offline mode.
- Dependencies: Identity, Agents, Capabilities, Runtime, Distribution, Security, Performance.
- Acceptance: deterministic policy constraints, no trust downgrade, partition handling and no hidden data residency violation.

## P06 — Agents

**Purpose:** manage agent identity, registration, skill declarations, delegation, collaboration and lifecycle.

- Inputs: agent identity/attestation, skill manifest, task and principal binding, scoped delegation.
- Outputs: dispatch assignment, agent result, collaboration/dissent artifacts, lifecycle events.
- Owner: `core/agent_fabric.py`, `core/agent_identity.py`, `core/agent_mesh.py`, supervisor/coordination.
- Authority: skills describe capability; only canonical grants authorize use; delegation cannot exceed delegator scope.
- State: proposed → registered → trusted-for-scope → active → suspended/revoked/retired.
- Failure: identity mismatch, replay, untrusted skill, supervisor loss or agent crash → isolate, revoke or mark incomplete.
- Budgets: agent count, delegation depth, task fan-out, per-agent compute/time and message size.
- Observability: agent ID/key epoch, skill version, task/execution binding, dispatch and result lineage.
- Recovery: revoke compromised agent; reassign only after reauthorization; retain forensic events.
- Dependencies: Identity, Security, Routing, Capabilities, Cognition, Runtime, Audit.
- Acceptance: principal/task/execution binding, privilege non-escalation, isolation and revocation races.

## P07 — Capabilities

**Purpose:** represent narrow, expiring, revocable authority for an exact principal, action, target and scope.

- Inputs: authenticated principal, policy decision, requested action, target, execution context.
- Outputs: grant/deny result and capability reference with scope/expiry/constraints.
- Owner: `noryx7_runtime/capabilities.py`, policy and authorization boundary.
- Authority: canonical authority plane; no model, plan, route, semantic claim or simulation may mint grants.
- State: requested → evaluated → granted/denied → consumed/revoked/expired.
- Failure: unknown, ambiguous, expired, replayed, revoked or mismatched grant → deny.
- Budgets: grant lifetime, scope size, call count, target set and concurrent use.
- Observability: request, policy version, grant scope, use, revocation and denial reason; never expose secret material.
- Recovery: immediate revocation and epoch change; stale caches fail closed.
- Dependencies: Identity, Policy, Runtime, Security, ActionGate, Audit.
- Acceptance: deny-by-default, scope confinement, replay prevention and revocation propagation.

## P08 — Tools

**Purpose:** provide typed adapters for external/local operations with explicit inputs, outputs and isolation.

- Inputs: action envelope, registered adapter identity, capability reference, validated arguments.
- Outputs: typed result, side-effect receipt, output provenance and error classification.
- Owner: `core/tools.py`, `core/actions.py`, `noryx7_runtime/adapters.py`.
- Authority: adapters execute only the exact authorized action; adapter registration is not user authorization.
- State: registered → admitted → invoked → result-captured → verified/quarantined.
- Failure: malformed args/result, timeout, adapter identity mismatch or sandbox failure → stop and quarantine result.
- Budgets: argument/result bytes, calls, wall time, CPU/memory, filesystem and egress.
- Observability: adapter version, action digest, capability reference, execution outcome and side-effect evidence.
- Recovery: terminate sandbox, revoke adapter/session, reconcile side effects via explicit compensation contract.
- Dependencies: Capabilities, Security, Runtime, Routing, Audit, Recovery.
- Acceptance: injection resistance, output validation, no ambient host authority and exact action/result binding.

## P09 — Memory

**Purpose:** manage task context, hierarchical memory, secure persistence, retrieval and lifecycle.

- Inputs: verified memory proposals, source/evidence references, retention and purpose policy.
- Outputs: scoped retrieval results, memory records, lineage and expiry/deletion events.
- Owner: `core/memory.py`, `core/memory_hierarchy.py`, `core/secure_memory.py`.
- Authority: memory is data, never a source of permission or truth solely by storage.
- State: proposed → validated → admitted → active → expired/quarantined/deleted.
- Failure: provenance loss, poisoning indicator, scope mismatch, quota or storage integrity error → reject/quarantine.
- Budgets: per-tenant and per-execution bytes/items, retrieval count, retention and cache limits.
- Observability: memory ID/version, provenance, access principal, scope, retention and lifecycle.
- Recovery: restore from verified checkpoint; preserve deletion tombstones and prevent stale replica resurrection.
- Dependencies: Identity, Privacy, Evidence, NEXUS, Runtime, State, Audit, Distribution.
- Acceptance: tenant/execution isolation, poisoning resistance, deterministic scope, retention/deletion and restore integrity.

## P10 — Runtime

**Purpose:** own execution lifecycle, scheduling, deadlines, cancellation, idempotency and dispatch orchestration.

- Inputs: validated plan, execution identity, policy snapshot, scoped grants, resource reservation.
- Outputs: lifecycle events, adapter dispatch, result envelope, completion/failure state.
- Owner: `noryx7_runtime/engine.py`, lifecycle, scheduler and core runtime.
- Authority: runtime enforces but does not redefine policy or create trust roots.
- State: created → admitted → scheduled → running → verifying → committed/failed/cancelled/expired.
- Failure: invalid transition, deadline, scheduler failure, exception or partial dispatch → stop, record and reconcile.
- Budgets: wall time, actions, concurrency, queue depth, memory, retries and output size.
- Observability: execution ID, state transitions, queue/scheduler metrics, cancellation and adapter receipts.
- Recovery: checkpoint only at declared safe points; replay idempotently; no duplicate external effects.
- Dependencies: Planning, Routing, Agents, Capabilities, Tools, Security, State, Audit, Performance.
- Acceptance: lifecycle invariants, cancellation races, deadline propagation, replay/idempotency and bounded scheduling.

## P11 — Security

**Purpose:** establish identity, authentication, secure channels, authorization integration, key lifecycle, perimeter and isolation.

- Inputs: identity claims, cryptographic artifacts, channel metadata, policy request and threat signals.
- Outputs: authenticated context, integrity result, allow/deny/isolate recommendation to canonical policy/action gates.
- Owner: `core/security.py`, `core/crypto.py`, secure channel, identity, key lifecycle and perimeter.
- Authority: security mechanisms enforce identity/integrity; policy decides authorization; cryptographic validity is not permission.
- State: untrusted → authenticated → authorized-for-specific-action (via policy) → revoked/expired/quarantined.
- Failure: bad signature, unknown key, replay, epoch mismatch, compromised trust anchor or verifier exception → deny/isolate.
- Budgets: crypto operation limits, nonce/sequence windows, handshake time, key rotation and rate limits.
- Observability: security events, key IDs/epochs, trust transitions and verification outcomes; secrets excluded.
- Recovery: revoke keys/principals, lockdown affected zones, rotate and re-attest from trusted roots.
- Dependencies: Identity, Capabilities, Runtime, Distribution, State, Audit, Recovery, Supply Chain.
- Acceptance: adversarial protocol tests, replay/retarget resistance, key revocation and no confused-deputy bypass.

## P12 — State

**Purpose:** own authoritative transitions, journal, attestation references and atomic commit/recovery semantics.

- Inputs: verified result, execution context, expected state version, provenance and commit proposal.
- Outputs: accepted/rejected transition, durable journal entry and new state version.
- Owner: `noryx7_runtime/state.py`, core state and journal.
- Authority: sole trusted-state commit boundary; cannot accept an unverified or stale proposal.
- State: proposed → validated → committed/rejected; journal sequence is monotonic per declared chain.
- Failure: digest/signature mismatch, stale version, duplicate/reordered entry or storage failure → reject and preserve prior state.
- Budgets: transaction size, journal growth, lock duration, write rate and retention.
- Observability: transition ID, predecessor digest, actor, execution, verifier references and commit outcome.
- Recovery: atomic checkpoint/restore with chain continuity; rollback never silently erases forensic history.
- Dependencies: Runtime, Verification, Security, Memory, Audit, Recovery, Distribution.
- Acceptance: tamper/replay/order tests, atomicity, crash consistency and restore chain continuity.

## P13 — Distribution

**Purpose:** place workloads and state across device, edge, cloud and offline nodes with explicit trust and partition semantics.

- Inputs: node identity/attestation, placement constraints, data classification, route proposal and network health.
- Outputs: admitted placement, remote dispatch, replication/synchronization and node health state.
- Owner: `core/distributed.py`, device fabric, offline adapters and `ecosystem/global_scale.py`.
- Authority: remote nodes never inherit global authority; each operation uses scoped identity/capabilities.
- State: discovered → attested → admitted → active → degraded/partitioned/revoked/rejoining.
- Failure: partition, stale attestation, divergent journal, node compromise or sync conflict → isolate/degrade; do not accept stale authority.
- Budgets: node count, shard size, replication factor, bandwidth, queue depth and sync window.
- Observability: node/epoch, placement, replication lag, partition and rejoin events.
- Recovery: re-attestation, conflict reconciliation and verified snapshot; offline/cloud fallback remains explicit.
- Dependencies: Identity, Security, Runtime, State, Memory, Routing, Recovery, Performance.
- Acceptance: partition/failover, replay, stale node, split-brain and offline recovery scenarios.

## P14 — Interfaces

**Purpose:** expose bounded user and operator interaction surfaces with consistent consent and action boundaries.

- Inputs: user intent, session state, accessibility/input events, display permissions.
- Outputs: rendered information, user confirmations, explicit action requests and interaction receipts.
- Owner: JARVIS, NORYX Browser, API/platform and interaction/orchestration adapters.
- Authority: surfaces do not bypass policy or capability checks; browser v0.1 remains isolated by its declared baseline.
- State: session lifecycle, navigation/workflow state and confirmation state; no hidden cross-product authority.
- Failure: malformed request, session swap, UI spoofing, navigation/policy violation or gateway unavailable → deny or safe offline presentation.
- Budgets: request/response size, session count, navigation rate and local resource limits.
- Observability: surface version, session/correlation IDs, confirmation and action references; minimize content logs.
- Recovery: invalidate compromised session/surface, preserve safe local state and require reauthentication.
- Dependencies: Ingress, Understanding, Identity, Orchestration, Runtime, Policy, Audit.
- Acceptance: boundary tests, session isolation, explicit consent, accessibility and no ambient privileges.

## P15 — Audit

**Purpose:** preserve tamper-evident records of security, execution, state, provenance and lifecycle events.

- Inputs: signed/structured event records from trusted boundaries and untrusted observations marked accordingly.
- Outputs: append-only/tamper-evident event chains, searchable audit views and evidence bundles.
- Owner: `core/audit.py`, `core/observability.py`, runtime audit and state journal.
- Authority: audit supplies evidence; it does not authorize or mutate system state.
- State: event-created → validated → appended → checkpointed → retained/expired under policy.
- Failure: missing sequence, invalid chain, storage exhaustion or clock anomaly → raise integrity incident; preserve raw forensic artifacts where safe.
- Budgets: event size/rate, retention, storage, indexing and query scope.
- Observability: chain health, dropped-event counters, sequence and checkpoint status.
- Recovery: restore from verified checkpoint; never silently rewrite history; mark gaps explicitly.
- Dependencies: all planes; especially Security, Runtime, State, Recovery and Privacy.
- Acceptance: tamper, truncation, reordering, gap detection, retention and tenant-safe query.

## P16 — Recovery

**Purpose:** contain incidents and restore only verified, authorized components and state.

- Inputs: incident signals, trusted recovery catalog, backup/checkpoint digests, operator approval and target epoch.
- Outputs: containment actions, recovery plan, restored state and re-attestation report.
- Owner: `core/recovery.py`, defense, runtime recovery and state restore.
- Authority: recovery can invoke narrowly defined containment/restore procedures; it cannot silently weaken trust policy.
- State: detect → classify → contain → preserve → restore → re-attest → monitor → close.
- Failure: corrupted backup, untrusted component, stale epoch or incomplete restore → quarantine and stop.
- Budgets: recovery time, restore size, retries, isolated resources and evidence retention.
- Observability: incident ID, scope, actions, approvals, source artifact and verification result.
- Recovery: recovery is the plane; its own bootstrap requires independent root-of-trust and documented manual fallback.
- Dependencies: Security, Identity, State, Audit, Supply Chain, Distribution, Human Control.
- Acceptance: partial restore, rollback, repeated incident, compromised backup and simultaneous failures.

## P17 — Performance

**Purpose:** define predictable resource admission, latency/throughput objectives, degradation and capacity management.

- Inputs: workload class, risk, SLO target, resource estimate, node capacity and priority policy.
- Outputs: admission/reservation decision, budget profile, telemetry and safe degradation state.
- Owner: limits, resource router, scheduler, observability and global-scale architecture.
- Authority: performance optimization cannot lower security, verification, privacy or authorization requirements.
- State: estimated → admitted/rejected → running → measured → released/degraded.
- Failure: saturation, starvation, runaway queue, deadline miss or noisy-neighbor behavior → backpressure, shed load or degrade explicitly.
- Budgets: CPU/GPU/memory/storage/network, concurrency, queue length, latency, energy and cost.
- Observability: p50/p95/p99 latency, throughput, saturation, queue wait, error and cost by workload/tenant.
- Recovery: circuit-break, shed/retry within limits, reschedule only with idempotency and re-evaluate capacity.
- Dependencies: Runtime, Routing, Distribution, Agents, Tools, Audit, Business/tenant metering.
- Acceptance: percentile and endurance targets, fairness, isolation, overload behavior and graceful degradation.

## P18 — Universal Intelligence

**Purpose:** supply specialist domain reasoning, evidence assessment, uncertainty and cross-domain composition on the common substrate.

- Inputs: domain task, ontology/schema, evidence references, validity scope and specialist route.
- Outputs: domain assessment, specialist result, uncertainty, limitations and escalation requirement.
- Owner: `core/universal_intelligence.py`, subtask UIF and domain adapters.
- Authority: domain conclusions do not grant permissions or commit trusted state.
- State: routed → evidence-bound → assessed → cross-checked → accepted-for-scope/indeterminate/rejected.
- Failure: unsupported domain, missing expert evidence, contradictory source or out-of-domain model → escalate/indeterminate.
- Budgets: specialist count, evidence count, source freshness, compute and domain-specific risk budget.
- Observability: domain/schema version, source lineage, method, uncertainty and reviewer references.
- Recovery: invalidate assessments when source/model validity expires; preserve previous versions and supersession links.
- Dependencies: NEXUS, Knowledge, Cognition, Memory, FRL, Audit, Human Control.
- Acceptance: contradiction retention, uncertainty calibration, domain validity and correct escalation.

## 19. Cross-plane dependency constraints

The canonical enum has 19 values. The architecture closure register must not create a second enum or reorder existing identifiers. Cross-cutting domains such as NEXUS, FRL, Mirror World, Knowledge, Privacy and Human Control map onto these planes; they are not additional canonical planes unless a separately reviewed ADR changes the registry.

Mandatory dependency directions:
- surfaces → ingress → identity/context → planning/cognition;
- cognition/planning → routing → agents/tools/runtime;
- capabilities/policy/security gate all privileged dispatch;
- result verification → state commit → memory/audit;
- distribution transports scoped execution but does not widen authority;
- recovery consumes trusted audit/state/supply-chain evidence;
- performance constrains execution but cannot weaken any trust invariant.

## 20. Architecture status discipline

For each plane track separately:
- architecture status: inventoried / architected / reviewed / frozen;
- implementation status: absent / partial / implemented;
- verification status: none / component / integrated / operational assessment;
- source evidence: exact repository path and revision;
- unresolved decisions and owner.

No status is inferred from file existence, registry presence or documentation prose alone.
