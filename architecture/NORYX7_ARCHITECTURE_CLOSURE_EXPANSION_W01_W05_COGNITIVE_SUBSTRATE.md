# NORYX7 — Architecture Closure Expansion W01–W05 and Shared Cognitive Substrate

**Status:** source-reconciled architectural proposal; all decisions remain open unless explicitly marked observed  
**Date:** 2026-11-22  
**Source snapshot:** repository `main` as inspected on 2026-11-22; file paths and blob anchors are listed in the traceability ledger  
**Scope:** architecture only. No runtime code, tests, dependencies, integration, merge or deployment.

## 1. Executive architecture findings

The current repository already contains substantial bounded mechanisms, but several similarly named abstractions have different semantics and are not yet one canonical service. This is not automatically a defect: separate components can remain separate if ownership, lifecycle, contracts and precedence are explicit.

The principal findings are:

1. **Task identity is not yet a single cross-front lifecycle contract.** Core `TaskSpec`, JARVIS `Request`/`Plan`, RuntimeEngine execution identity and four-front `IntentEnvelope` have related but distinct identity fields.
2. **There are multiple agent selection/dispatch abstractions.** `AgentMesh`, `AgentCoordinator`, `AgentFabric`, `AgentSupervisor`, `OperationalAgentFabric`, and the HYPERSYNTH allocation loop overlap but are not interchangeable.
3. **The declared cognitive pipeline is richer than its current simulator.** `InternalSimulator` checks declared hypothesis shape/identity and a simple feasibility predicate; it is not a physical, economic, software or causal simulator.
4. **Parallelism is not equivalent to multi-agent presence.** The inspected HYPERSYNTH path assigns bounded agents but executes its assignments sequentially. Other abstractions have separate allocation behavior. A canonical scheduler must own concurrency, dependencies, cancellation and result ordering.
5. **Provider routing, execution authorization and resource placement are distinct.** `ProviderRouter`, `ProviderExecutionGateway`, `ExecutionFabric`, `ResourceRouter`, `ModelFabric` and the runtime scheduler require a single contract graph without collapsing their responsibilities.
6. **Memory has multiple implementations and assurance levels.** Core bounded memory, L0–L5 hierarchy, JARVIS memory, task context, global fabric and durable journals have different storage, provenance, isolation and deletion semantics.
7. **Multimodal references bind digest and locator, but locator classification and data lifecycle remain open.** A digest does not provide confidentiality, permission, availability or safe locator resolution.
8. **User-understanding and self-improvement are proposal-oriented abstractions, not unrestricted authorities.** Consent, profile lifecycle, admission authority and rollback need explicit governance.

These findings add no canonical plane. The count remains **18**, anchored by `core/architecture_gate.py`.

## 2. W01 — Principal, identity and authority contract

### 2.1 Identity object taxonomy

NORYX7 must distinguish at least:
- **Human principal:** accountable person or organization acting through an authenticated session.
- **Organization/tenant principal:** legal or organizational boundary with membership and delegated roles.
- **Workload identity:** service, runtime, agent, model adapter, job or deployment instance.
- **Agent identity:** a cryptographically identified agent workload, not a personality or display name.
- **Device identity:** enrolled hardware/platform identity and attestation state.
- **Session identity:** short-lived authenticated interaction context, audience-bound and revocable.
- **Execution identity:** unique bounded lifecycle for one task/action chain.
- **Artifact identity:** immutable digest and release provenance for code, model, firmware, schema or policy.
- **Evidence identity:** stable identifier and lineage for a source, observation, inference or verification artifact.

Identifiers are not interchangeable. A browser client ID is not a verified human principal; an agent ID is not an authorization grant; a request ID is not a durable idempotency key; a digest is not a signature.

### 2.2 Authority graph

Authority is a directed, time-bounded relationship:
`issuer → subject → capability → resource/scope → constraints → validity → revocation state`.

A grant must bind:
- issuer identity and issuer authority;
- subject principal/workload/device;
- capability/action and target/resource;
- tenant and data scope;
- contextual conditions and risk class;
- not-before/expiry;
- policy and schema version;
- nonce or one-use authorization ID where required;
- revocation epoch/reference;
- signature or authenticated channel evidence.

Delegation cannot expand the issuer's scope. A child grant is a strict subset of the parent's authority and cannot survive parent revocation or expiry unless an explicit independent authority reissues it.

### 2.3 Observed boundaries and gaps

- `core/agent_fabric.py` binds AgentCore, AgentIdentity, skills and a principal-authorization callback, and rechecks trust during dispatch.
- `core/identity.py`, `core/agent_identity.py`, `core/attestation.py`, `core/trust_chain.py` provide separate identity and attestation primitives.
- `gateway/auth.py` creates a short-lived HMAC session from bootstrap authentication. `gateway/runtime_adapter.py` maps the client identifier into task context; a client identifier alone does not establish a verified human principal.
- `jarvis/security/authorization.py` stores explicit principal/capability/target grants in an in-memory set. Its abstraction does not by itself define signed grants, expiry, issuer lineage, persistent revocation or cross-instance consistency.
- `jarvis/context/authorized.py` authorizes source acquisition through a callback, but the returned provenance string is a source label, not cryptographic provenance.

### 2.4 Normative authority lifecycle

`ENROLL → VERIFY_IDENTITY → ATTEST (where applicable) → ISSUE → DELEGATE (subset only) → USE → REVALIDATE → EXPIRE/REVOKE → AUDIT`.

Revalidation points are mandatory at privileged dispatch and result admission. Long-running tasks must declare whether revocation is checked continuously, at checkpoints or before each irreversible effect. A task cannot assume authority remains valid merely because it was valid at planning time.

## 3. W02 — Canonical request, task and execution lifecycle

### 3.1 Distinct identifiers

Define these separate identifiers:
- `interaction_id`: user-facing conversation/interaction grouping;
- `request_id`: one submitted request at a front boundary;
- `task_id`: logical work item, possibly decomposed;
- `execution_id`: one concrete attempt/lifecycle of a task;
- `step_id`: one node in an immutable execution plan;
- `action_id`: one proposed effect;
- `authorization_id`: one grant/use authorization;
- `idempotency_key`: stable key for deduplicating a requested effect;
- `correlation_id`: tracing relationship across services;
- `causation_id`: identifier of the event that caused this event.

Retries may create a new execution attempt while retaining the logical task and original request reference. An idempotency key must remain stable for the same intended external effect across retries; it must not be regenerated merely because a worker restarted.

### 3.2 Canonical lifecycle

`RECEIVED → NORMALIZED → AUTHENTICATED → AUTHORIZED_FOR_PLANNING → CONTEXT_READY → DECOMPOSED → PLANNED → PLAN_VERIFIED → SCHEDULED → DISPATCH_RESERVED → EXECUTING → RESULT_RECEIVED → RESULT_VERIFIED → ADMITTED → COMMITTED → CLOSED`.

Terminal and non-success states:
`REJECTED`, `CANCELLED`, `EXPIRED`, `TIMED_OUT`, `INDETERMINATE`, `PARTIAL`, `FAILED`, `QUARANTINED`, `COMPENSATION_REQUIRED`.

A timeout or transport disconnect after dispatch is **indeterminate**, not proof of failure. The caller must query by idempotency/execution reference before retrying a non-idempotent external effect.

### 3.3 One lifecycle owner

A canonical lifecycle coordinator owns state transitions and correlation. Front runtimes and cognitive kernels may contribute typed stages, but must not independently commit the same logical execution. The architecture must designate whether RuntimeEngine or a higher-level ExecutionLifecycle owns dispatch reservation, cancellation, result admission and closure. JARVIS request state and RuntimeEngine step state remain distinct stores until cross-store transaction semantics are decided.

### 3.4 Result and commit boundary

A result is admissible only when it binds:
- request/task/step/execution identity;
- selected workload and artifact version;
- output digest and typed output schema;
- provenance/evidence references;
- verification contract and result;
- policy/authorization reference;
- completion/partial/indeterminate status;
- resource/deadline accounting.

Memory write, task completion, billing/metering and user-visible success are downstream effects with their own commit/idempotency contracts. They must not be treated as one atomic transaction without an explicit transaction coordinator or outbox protocol.

## 4. W03 — Memory, context, state and knowledge architecture

### 4.1 Separate storage classes

Memory and state must be classified by semantics, not merely by L0–L5 labels:

| Class | Purpose | Authority | Required durability |
|---|---|---|---|
| L0 active working set | Current inference/task | None | Volatile |
| L1 interaction context | Bounded current interaction | None | Session-scoped |
| L2 task memory | Execution-scoped intermediate results | None | Task lifecycle |
| L3 user-approved persistent memory | User preference/continuity | None | Durable, revocable |
| L4 domain knowledge | Versioned facts/evidence/models | None | Durable, provenance-bearing |
| L5 system/security state | Identity, revocation, journal, audit, monotonic epochs | Security/control authority only | Durable and tamper-evident |

L5 is not a “more important memory” bucket: it is a distinct control-state domain and must not share mutation authority with model-generated semantic memory.

### 4.2 Observed implementations

- `core/memory.py`: bounded in-memory `MemoryStore`, deep-copy isolation, kinds `working/local/edge/cloud/long_term/suspended`, execution filtering and deletion by ID. It does not declare durable persistence, per-tenant access policy, retention schedule, provenance signature or tombstone replication.
- `core/memory_hierarchy.py`: bounded L0–L5 records and explicit promotion, but the record is a simple key/value/level tuple and does not carry source, consent, tenant, expiry, lineage or cryptographic integrity.
- `core/context.py`: per-task versioned snapshots and optional memory hydration. Memory listing errors are caught and treated as empty memory; this creates a potential silent loss-of-context distinction that the architecture must represent explicitly.
- `jarvis/memory/store.py`: separate in-memory key/value store with capacity bound but no execution isolation, provenance, deep-copy contract, retention or deletion protocol.
- `ecosystem/global_fabric.py`: in-memory global memory/identity metadata; not a durable distributed store.
- `core/state_journal.py`, `noryx7_runtime/state.py`, `jarvis/core/state.py`: separate state domains requiring canonical ownership and reconciliation decisions.

### 4.3 Memory record contract

A persistent record must include:
- record ID, tenant/principal scope and memory class;
- content type/schema and encrypted payload reference;
- source/evidence IDs and provenance chain;
- creation/update/expiry timestamps;
- consent/legal basis and purpose;
- retention and deletion policy;
- sensitivity/compartment label;
- integrity digest and optional signature;
- model/agent writer identity and execution ID;
- confidence/uncertainty as descriptive metadata, never authority;
- promotion/acceptance decision and reviewer/policy reference;
- replication/tombstone state.

### 4.4 Poisoning, correction and deletion

Memory admission is separate from memory retrieval. Model output, tool output, user content and external sources receive distinct trust labels. Promotion to persistent knowledge requires evidence review and scope. Contradictory records coexist with explicit status; do not overwrite by recency alone. Corrections preserve prior versions and reason. Deletion must propagate tombstones to replicas, caches, indexes, embeddings, derived profiles and offline copies, subject to legally required retention exceptions. A deletion request cannot erase immutable security audit evidence where retention is legally required; that exception must be explicit and minimized.

### 4.5 Context degradation

If memory retrieval fails, the runtime must produce an explicit `context_degraded` state with affected sources and downstream restrictions. Silent empty-context fallback is not semantically equivalent to a successful retrieval of no relevant records. High-consequence workflows may require refusal or user confirmation when required context is unavailable.

## 5. W04 — Agent topology, delegation and scheduling

### 5.1 Observed abstractions

- `core/agent_mesh.py`: role-based registry and deterministic lexicographic selection of the first matching role.
- `core/coordination.py`: assigns plan steps up to `max_agents`, applies ActionGate, rechecks identity, validates result and verifies equality for consensus.
- `core/agent_fabric.py`: bounded skill/identity/principal authorization dispatch.
- `core/agent_runtime.py`: per-runtime lifecycle status and heartbeat based on live identity trust.
- `core/operational_fabric.py`: router → supervisor → agent selection/execution/result admission.
- `core/hypersynth.py`: performs decomposition, specialist routing, plan verification, hypothesis/simulation, allocation and sequential agent execution in its current run path.
- `core/supervisor.py` and `core/agent_fabric.py` provide different selection/dispatch semantics; neither should be silently assumed to be the sole canonical owner.
- JARVIS has its own `JarvisOrchestrator` and provider boundary, with an optional bridge to core capability registry.

### 5.2 Canonical separation of responsibilities

1. **Agent Registry:** agent identity, artifact version, skills, domain scope and lifecycle.
2. **Agent Health/Liveness:** heartbeat, readiness, saturation and quarantine state.
3. **Delegation Authority:** whether principal/workload may delegate a specific task and data scope.
4. **Task Decomposer:** produces task DAG and dependencies.
5. **Scheduler:** orders ready DAG nodes, respects deadline, resource and fairness budgets.
6. **Allocator:** selects eligible agent/workload for a ready node.
7. **Executor:** dispatches the immutable step through the privileged boundary.
8. **Result Admission:** validates identity, schema, provenance, execution binding and evidence.
9. **Consensus/Dissent:** compares independently produced outputs; it is not an authorization or truth oracle.
10. **Supervisor:** handles cancellation, timeout, failure, quarantine and escalation.

### 5.3 Parallel execution contract

A plan is a directed acyclic graph. A node is eligible only when all dependencies are admitted. Parallel execution is permitted only for independent nodes and bounded by:
- max concurrent tasks per tenant and workload;
- agent/model capacity;
- resource budget and deadline;
- data classification and trust zone;
- rate limits and provider quota;
- fairness and priority policy;
- cancellation and failure propagation rules.

The scheduler must specify whether failure stops descendants, allows independent branches to finish, or enters partial-result mode. A partial result is explicitly marked and cannot be promoted to full task completion.

### 5.4 Diversity and consensus

Agent role, skill, model family, training/provider lineage and evidence source are dimensions of independence. Multiple agent IDs do not guarantee independent reasoning if all use the same model, prompt, source corpus or toolchain. Consensus must report dependency overlap and dissent. Majority vote is not a substitute for evidence or a formal verifier.

## 6. W05 — Provider, model, resource and execution routing

### 6.1 Four separate decisions

- **Model/provider routing:** which model/provider can satisfy a cognitive capability under quality, privacy, cost and availability constraints.
- **Agent allocation:** which trusted agent executes a task/step.
- **Resource placement:** device, edge, cloud or specialized hardware placement.
- **Action dispatch:** whether an exact principal may execute an exact action against an exact target now.

These decisions may exchange constraints, but one cannot grant the authority of another.

### 6.2 Observed source behavior and gaps

- `core/provider_router.py`: deterministic first-capability match and exception-based failover across registered providers.
- `core/provider_execution.py`: selects a provider and routes its handler through `ExecutionFabric` and a caller-supplied authorization callback. The gateway currently resolves a provider before the execution boundary; its behavior is not equivalent to the provider router's own retry loop.
- `core/resource_router.py`: deterministic device/edge/cloud choice from complexity, privacy and latency flags. It does not inspect live capacity, jurisdiction, data residency, current cost, queue saturation, energy or measured latency.
- `core/agent_fabric.py`, `core/operational_fabric.py`, `core/coordination.py`: agent selection and dispatch responsibilities.
- `core/hypersynth.py`: allocation is a separate stage after cognitive plan/simulation.
- `core/limits.py`, `ecosystem/global_scale.py`: bounded local resource primitives and simulated regional/cell capacity, not evidence of production fleet telemetry.

### 6.3 Canonical route request

A route decision consumes a versioned `RouteRequest`:
- task/step and execution identity;
- required capability and quality profile;
- risk and consequence class;
- data classification, consent and allowed processing regions;
- latency/deadline and availability target;
- compute/memory/context budget;
- cost ceiling and billing policy;
- provider/model/agent allow/deny constraints;
- required tool permissions and execution scope;
- fallback policy and whether fallback changes semantics;
- audit/correlation references.

A route result includes selected candidate, reason codes, policy/version, expected cost/latency envelope, resource placement, data residency, degraded/fallback state and expiry. The final action dispatcher still reauthorizes the concrete effect.

### 6.4 Safe failover

Provider failure is not always safe to retry. Retry policy must classify:
- pre-dispatch failure (safe to select another provider);
- request accepted but no response (indeterminate);
- response received but invalid (quarantine result; retry only under declared idempotency);
- side effect may have occurred (reconcile before retry);
- provider compromised/revoked (contain and revoke credentials).

A fallback must not silently move sensitive data to a less trusted provider or a prohibited jurisdiction. If no route satisfies the policy, return a typed `no_eligible_route` or `route_indeterminate` result.

## 7. Shared cognitive substrate — NEXUS, HYPERSYNTH, FRL and multimodal data

### 7.1 Semantic and execution separation

HYPERSYNTH cognition produces proposals, hypotheses, plans and assessments. NEXUS supplies typed semantic representations and wire contracts. FRL supplies formal-proof artifacts and checker results. The execution fabric alone dispatches authorized actions. These layers must not share one undifferentiated “intelligence result” object.

### 7.2 Cognitive evidence stages

`PROPOSED → STRUCTURALLY_VALID → EVIDENCE_LINKED → INDEPENDENTLY_CHECKED → ADMISSIBLE_FOR_SCOPE`.

Distinct result classes:
- model-generated proposal;
- retrieved source;
- direct observation;
- deterministic computation;
- simulation output;
- empirical result;
- formal proof;
- expert review;
- policy decision.

Confidence and consensus remain metadata. They do not upgrade a proposal into a proof or an observation into a causal explanation.

### 7.3 Current reasoning and simulator boundary

- `core/reasoning.py` generates hypotheses from plan steps and checks structural consistency.
- Its `InternalSimulator` currently checks a bounded feasibility predicate over the declared plan; it is not a domain-calibrated world simulator.
- `core/metacognition.py` validates stage/identity/count correspondence and computes a confidence value from successful checks. That value is a pipeline-integrity ratio, not a calibrated probability that the output is true.
- `core/universal_intelligence.py` uses a bounded domain vocabulary and evidence-strength/risk/contradiction routing. Its output is routing metadata, not specialist certification.
- `core/verification.py` provides contract/output checks; schema validity is not semantic truth.

### 7.4 Multimodal lifecycle

`core/multimodal.py` defines text/image/audio/video/document modalities and `MediaRef` with content type, digest and locator. The architecture must add:
- locator type allowlist (local handle, encrypted object reference, approved URL, ephemeral stream);
- no arbitrary path traversal, URL fetch or SSRF through model-supplied locators;
- owner/tenant and access policy;
- content size, duration, page/frame and decompression limits;
- malware/content scanning and parser isolation;
- consent, purpose, retention and deletion propagation;
- encryption and key scope;
- provenance and transformation lineage;
- derived artifact references and redaction;
- model/provider disclosure and region policy.

A digest proves content identity relative to bytes; it does not encrypt, authorize, sanitize, retain or retrieve the media.

## 8. W01–W05 cross-stream dependency and decision table

| ID | Priority | Decision | Affected streams | Required output |
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

These are open decisions, not accepted ADRs.

## 9. Architecture risk register

| Risk | Classification | Why it matters | Required disposition |
|---|---|---|---|
| Multiple agent dispatch abstractions | AMBIGUOUS / DUPLICATE | Selection and authorization semantics may diverge | Name canonical owners and compatibility roles |
| Sequential HYPERSYNTH execution despite multi-agent framing | AMBIGUOUS | Product expectation and actual scheduling semantics differ | Define concurrency contract before implementation |
| Plan truncation by agent limit in coordinator | CONTRACT GAP | May silently omit work if caller assumes full DAG completion | Explicit partial-plan rejection or scheduler-owned batching |
| Task context memory errors swallowed | UNSAFE-FALLBACK | Missing context may look like empty context | Typed degraded-context state and risk policy |
| Multiple memory stores with different guarantees | DUPLICATE / HIDDEN-COUPLING | Cross-front retrieval/deletion can diverge | Memory authority and data lifecycle decision |
| Provider fallback after uncertain dispatch | UNBOUNDED SIDE EFFECT RISK | Duplicate external effects | Idempotency/reconciliation before retry |
| Resource router ignores live placement constraints | UNSUPPORTED | A tier selection is not live capacity or residency proof | Route request with trusted telemetry and policy |
| Multimodal locator is opaque | UNBOUNDED / SECURITY | Digest does not make locator safe | Typed locator and isolated fetch contract |
| Metacognitive confidence interpreted as truth probability | UNVERIFIED | A check ratio is not empirical calibration | Rename semantics or calibrate by domain |
| User-understanding profile lifecycle incomplete | GOVERNANCE GAP | Consent to infer is not necessarily consent to retain indefinitely | Purpose/retention/deletion contract |

## 10. W01–W05 closure acceptance

A stream can move from PARTIAL to DECIDED only when:
1. every related class/module is mapped to exactly one primary responsibility;
2. callers and call graph identify lifecycle entry and exit;
3. principal and execution identity are carried without implicit casts;
4. retries, partial results, cancellation and indeterminate side effects have defined states;
5. data stores declare authority, retention, deletion and recovery;
6. resource selection and dispatch authorization are independent and auditable;
7. security and privacy boundaries are explicit for each surface and modality;
8. all open ADRs have a named decision owner and evidence requirement.

No implementation or verification status is implied by architectural documentation.

## 11. Explicit non-goals

This cycle does not authorize code changes, runtime refactors, wiring, schema migrations, tests, benchmarks, CI reruns, deployments, live provider calls, external side effects or production activation. The full integration and serious verification phase remains downstream of architectural closure.
