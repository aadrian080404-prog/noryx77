# NORYX7 — Agent Dispatch, Runtime Lifecycle and Plane-Registry Reconciliation

**Review date:** 2026-11-24  
**Source snapshot:** `main` at `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Scope:** architecture-only source reconciliation. No implementation, test, dependency, workflow, integration, deployment or baseline change is part of this record.

## 1. Executive disposition

The source review confirms that NORYX7 already contains several distinct, partially overlapping agent execution mechanisms and a separate RuntimeEngine execution kernel. The source does not justify collapsing these into one class or declaring any one of them globally canonical yet.

The architecture must distinguish at least four paths:

1. **Native principal-bound dispatch** — `core/agent_fabric.py` binds AgentCore, AgentIdentity and skills, then checks principal authorization before running an agent.
2. **Operational task dispatch and admission** — `core/operational_fabric.py` composes AgentSupervisor and a router; it selects an agent, runs it and admits the returned AgentResult.
3. **Explicit gated coordination** — `core/coordination.py` assigns plan steps, checks agent identity, verifies child tasks, passes execution through ActionGate, and performs result/output/consensus checks.
4. **Runtime action dispatch** — `noryx7_runtime/engine.py` schedules PlanStep values, authorizes configured high-risk actions, reserves a journal step, dispatches through an adapter/executor, verifies output, signs an attestation and commits.

These are different levels of the system. Agent selection, task execution, privileged action execution, result admission, and durable state commit are not interchangeable responsibilities.

## 2. Source evidence and exact boundaries

### 2.1 Native AgentFabric

`core/agent_fabric.py`:
- Registration requires an AgentBinding whose AgentCore and AgentIdentity IDs match, whose identity is well formed and trusted, and whose declared skills exist.
- Dispatch binds the supplied principal into request context and rejects context-principal spoofing.
- Candidate agents are visited in sorted ID order; failed agents, skill mismatches and untrusted identities are skipped.
- The injected `authorize_principal` callback is evaluated per candidate; callback exceptions fail closed for that candidate.
- The first eligible agent is run directly.

This is a concrete identity/skill/principal-gated native dispatch path. It does not itself express TaskSpec dependency scheduling, ActionGate execution, AgentResult admission, multi-agent consensus, or a durable execution journal. Its callback's issuer, policy version, revocation freshness and audit lineage remain external contracts.

### 2.2 OperationalAgentFabric and AgentSupervisor

`core/operational_fabric.py` composes AgentSupervisor with a router:
- `select` delegates task verification and agent selection to the supervisor.
- `dispatch` runs the selected agent and then calls `admit`.
- Execution exceptions are converted to a generic failed VerificationResult.
- The wrapper records selection/admission events only when an audit object is supplied.

`core/supervisor.py` verifies the task, selected agent identity/trust, task and execution binding, completion status, output, and result verification stage. This is a stronger task-result admission boundary than simple role lookup, but it is not a durable commit protocol and does not alone prove domain truth.

### 2.3 AgentCoordinator

`core/coordination.py` has a separate and more explicit gated path:
- Assignments are bounded by `max_agents`, but the current assignment loop truncates the plan to the first `max_agents` steps. This is a semantic policy, not merely a capacity setting; whether excess steps should be rejected, queued, delegated in waves, or explicitly marked deferred is unresolved.
- Each selected agent is re-resolved and trust-checked before execution and again after the run.
- Child tasks are verified; each run is wrapped in ActionGate authorization/execution.
- Result identity, task ID, execution ID, completion state and verification stage are checked; output is re-verified.
- Consensus currently requires distinct agent identities and equal outputs, plus matching task/execution identity and live trust checks.

The equality-based consensus is suitable only for deterministic/equivalent output contracts. It is not a universal consensus algorithm for probabilistic, evidence-based, numeric, multimodal or domain-specific outputs. Those require typed comparison policies, tolerance/uncertainty semantics and provenance-aware disagreement handling.

### 2.4 AgentMesh and AgentRuntime

`core/agent_mesh.py` is a small deterministic role selector: it registers nodes and returns the lexicographically first matching role. The `no_authorized_agent` error string does not by itself prove that authorization is performed; the inspected class contains no identity registry, capability check, liveness lease, capacity reservation or policy callback.

`core/agent_runtime.py` creates local status snapshots and refreshes heartbeat timestamps from a local clock. It checks identity trust through the supplied registry, but it is not a distributed heartbeat protocol: it has no remote lease expiry, signed heartbeat, failure detector, quorum, capacity reservation or cross-node fencing in this class.

Therefore Mesh discovery, Runtime liveness, AgentFabric authorization, OperationalFabric selection/admission and Coordinator gated execution must remain separate architectural roles until their callers and ownership are fully traced.

### 2.5 RuntimeEngine and Scheduler

`noryx7_runtime/scheduler.py`:
- rejects duplicate step IDs, missing dependencies and cycles;
- deterministically sorts all currently ready step IDs;
- emits a topological sequence.

`noryx7_runtime/engine.py` consumes that sequence in a normal sequential `for` loop. The scheduler therefore computes dependency-safe order; it does not execute independent DAG branches concurrently. Parallel scheduling would require a separately specified executor with bounded worker count, dependency barriers, cancellation propagation, per-step idempotency, shared-resource conflict rules, deterministic result ordering and partial-failure semantics.

RuntimeEngine's inspected path:
1. validates Intent, steps, verifier/executor and timeout;
2. creates an ExecutionLifecycle and rejects action-budget overflow;
3. computes a deadline and topological order;
4. checks deadline before each step;
5. creates a nonce-bearing ActionEnvelope and canonical action digest;
6. performs configured high-risk multi-authorization and replay checks;
7. reserves the step in the optional StateJournal before dispatch;
8. dispatches via adapter or executor;
9. verifies output and constructs an attestation, signing it when a signer is configured;
10. appends the attestation and calls the optional committer;
11. returns SUCCEEDED only after all ordered steps complete.

The journal reservation is an important duplicate-dispatch guard. It does not make the external side effect, attestation append and external committer a single atomic transaction. If dispatch succeeds but verification, attestation, append or commit subsequently fails, the caller may receive FAILED without a reliable statement about whether the external side effect happened. The reservation is deliberately retained/restored to prevent blind re-dispatch, but there is no first-class INDETERMINATE/RECONCILIATION_PENDING state in the inspected ExecutionStatus enum. A recovery protocol must query/reconcile the external effect using an idempotency key or authoritative adapter receipt; it must not infer “no side effect” from FAILED.

The inspected ExecutionStatus values are CREATED, RUNNING, SUCCEEDED, REJECTED, FAILED and CANCELLED. The lifecycle vocabulary is insufficient to represent partial completion, an uncertain external effect, compensation pending, quarantined output or reconciliation required.

## 3. Architecture contracts to resolve

### Contract A — canonical dispatch ownership

Define a responsibility graph, not a single monolithic “AgentFabric”:
- registry and enrollment;
- identity/trust and liveness;
- capability/skill matching;
- principal-to-agent delegation;
- task planning and DAG scheduling;
- allocation and lease/capacity reservation;
- ActionGate and privileged action authorization;
- execution adapter;
- result admission and semantic verification;
- consensus/disagreement resolution;
- state commit and audit.

Every callable dispatch entrypoint must map to one owner, an authority source, an execution ID, a policy version, a result-admission boundary and an audit correlation. Compatibility facades may remain, but must not silently create parallel authority paths.

### Contract B — lifecycle and side-effect certainty

Use distinct states for:
- **rejected before dispatch**;
- **running / dispatch intent recorded**;
- **succeeded and committed**;
- **failed with proven no side effect**;
- **indeterminate external effect**;
- **reconciliation pending**;
- **compensation pending**;
- **partially completed**;
- **quarantined / human review**;
- **cancelled before dispatch** versus **cancellation requested after dispatch**.

State transitions require durable event ordering and explicit ownership. A timeout after dispatch is not equivalent to a timeout before dispatch. Compensation is a new authorized action, not an automatic rollback assumption.

### Contract C — DAG scheduling semantics

Separate topological planning from actual execution concurrency. Specify:
- max parallel workers and per-domain concurrency;
- dependency barrier and result visibility;
- shared target/resource conflict detection;
- fairness, priority and starvation bounds;
- retry/idempotency and lease expiry;
- cancellation and deadline propagation;
- partial-result admission;
- deterministic replay and audit ordering;
- scheduler behavior when plan size exceeds capacity.

Until those contracts exist, sequential execution is the observed RuntimeEngine behavior and must not be described as parallel execution.

### Contract D — typed consensus

Consensus must be selected by output contract:
- exact equality only for canonical deterministic outputs;
- numeric tolerance and units for measurements;
- evidence intersection/independent-source requirements for factual claims;
- calibrated uncertainty and contradiction retention for probabilistic outputs;
- modality-specific comparison for images/audio/video;
- human or domain-expert escalation for high-consequence disagreement.

Agent count alone is not independence. Shared model/provider, prompt, evidence source, training lineage or toolchain must be represented in independence metadata before consensus strength is claimed.

### Contract E — plane registry evidence levels

`core/architecture_gate.py` defines exactly 18 canonical planes and validates required non-empty contract fields plus existence of recognized implementation path tokens. The inspected `core/architecture_registry.py` supplies definitions for all 18 and its referenced filename tokens resolve in the recursive source tree at the source snapshot.

This is a valid **structural presence** result only. It does not establish:
- that listed files implement the described contract;
- that all runtime call sites are mapped;
- that boundaries are enforced in production;
- that the referenced components are composed or reachable;
- that tests cover the declared regression target;
- that trust roots, recovery, observability or budgets work end to end;
- that the architecture is operationally ready or safe to freeze.

The structural gate and the evidence-backed architecture freeze gate must remain distinct. No plane count change is proposed.

## 4. Workstream impact

| Workstream | New source evidence | Remaining closure obligation |
|---|---|---|
| W01 Identity and authority | AgentFabric binds local agent identity and principal callback; AgentCoordinator rechecks trust | issuer taxonomy, callback trust root, delegation leases, revocation freshness, cross-front principal mapping |
| W02 Runtime topology/lifecycle | RuntimeEngine lifecycle and reservation/commit sequence mapped | composition-root/call-site graph, uncertain side-effect states, cross-store transaction and recovery |
| W03 State and memory | optional StateJournal reservation/append/restore behavior mapped | durable namespace, transaction boundaries, external-effect reconciliation, retention and recovery ordering |
| W04 Agent fabric | four distinct dispatch/selection/coordination mechanisms mapped | call-site graph, ownership, delegation, capacity, liveness and typed admission |
| W05 Routing/scheduling | deterministic topological ordering versus sequential execution confirmed | true concurrency contract, resource conflict, leases, fairness, retry and placement |
| W06 Evidence/FRL | equality consensus boundary and result-verification distinction mapped | typed evidence semantics, independence, uncertainty and domain-specific adjudication |
| W07 MIRROR WORLD | no new physical-world execution claim | model calibration, holdout, Reality Bridge authority and side-effect isolation |
| W08 Surfaces/distribution | execution and dispatch boundary distinction sharpened | surface identity parity, distributed fencing and offline reconciliation |
| W09 Security/trust | injected callbacks and live identity checks mapped | issuer, signed delegation, revocation, key custody and audit chain |
| W10 Domain assurance | consensus must be output/domain aware | qualified reviewer and validity manifests per domain |
| W11 Operations/reliability | cancellation/deadline and sequential execution semantics mapped | SLOs, telemetry, incident operations, reconciliation and capacity policy |
| W12 Ecosystem/governance | no business or community authority is implied by agent execution | separate financial, governance and impact ledgers |

All workstreams remain **PARTIAL**. This pass does not authorize implementation, integration or the comprehensive verification campaign.

## 5. New architecture decisions — proposals only

- **ADR-B85 — Canonical Agent Dispatch Ownership:** establish the responsibility graph and compatibility-facade rules across AgentFabric, OperationalAgentFabric, AgentCoordinator, AgentMesh, AgentRuntime, router and RuntimeEngine. Do not choose a single owner before call-site and constructor graph closure.
- **ADR-B86 — External Side-Effect Certainty and Reconciliation:** add explicit indeterminate/reconciliation/partial/compensation lifecycle semantics and define adapter receipts, idempotency keys, durable reconciliation and human escalation.
- **ADR-B87 — DAG Execution and Capacity Semantics:** distinguish deterministic topological ordering from concurrent execution; define bounded workers, conflict control, fairness, retry, cancellation and partial completion.
- **ADR-B88 — Typed Consensus and Independence:** define per-output comparison and evidence-independence requirements; do not treat identical outputs or agent count as universal proof.
- **ADR-B89 — Structural Registry vs Evidence-Backed Freeze:** preserve the 18-plane structural gate while requiring call-site, boundary, test, operational and trust evidence for freeze acceptance.

All five ADRs are **OPEN / PROPOSED**, not approved or frozen.

## 6. Source inventory reviewed

At source snapshot `7d900bc75843ea968aa5886d251dbfac83a5d93c`:
- `core/architecture_gate.py`
- `core/architecture_registry.py`
- `core/agent_fabric.py`
- `core/agent_mesh.py`
- `core/agent_runtime.py`
- `core/operational_fabric.py`
- `core/supervisor.py`
- `core/coordination.py`
- `noryx7_runtime/contracts.py`
- `noryx7_runtime/lifecycle.py`
- `noryx7_runtime/scheduler.py`
- `noryx7_runtime/engine.py`

The recursive tree contained 507 entries (426 blobs, 81 tree entries). All filename tokens in the 18-plane registry's implementation-boundary declarations resolved to a source path in this snapshot. This is a path-existence observation, not semantic validation.

## 7. Explicit non-actions

No Python/Kotlin/Swift/Go/Rust/TypeScript runtime source was edited. No tests were run or changed. No dependencies, workflows, deployments, baseline tags or frozen architecture contracts were modified. No PR was merged. This document records source evidence and open design obligations only.
