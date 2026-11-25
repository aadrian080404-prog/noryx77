# NORYX7 — Source-Level Authority, State and Effect Conflict Reconciliation

**Date:** 2026-11-25  
**Status:** bounded source inspection; architecture-only; unresolved contracts  
**Source baseline:** PR merge-base `7d900bc75843ea968aa5886d251dbfac83a5d93c`; inspected files are inherited source paths on the architecture branch.  
**Scope:** simultaneous W01–W12 cross-source review. No executable source, test, dependency, workflow, configuration or deployment changes.

## 1. Why this pass exists

The existing architecture documents define proposed canonical planes and handoffs. This pass compares those proposals against concrete source boundaries that can be mistaken for one another because they share names or similar responsibilities.

The strongest new finding is that NORYX7 currently has multiple independently useful local mechanisms for state journaling, identity, provider execution, agent routing and cross-front dispatch. Their local contracts are not yet evidence of one coordinated, durable, system-wide authority.

This is a bounded source inspection, not a complete dynamic call graph. A missing path or an uninspected caller is an explicit unknown, not proof of repository-wide absence or a proven vulnerability.

## 2. Source anchors inspected

| Source path | Blob SHA at inspected branch ref | Bounded observation |
|---|---|---|
| `web/app.py` | `a03d012d6f9f2fdbfb8a5e64397511e5ac692360` | FastAPI gateway routes and direct chat route |
| `gateway/auth.py` | `fa456172c99b183dcb2acd0ec99303ec540d2583` | Bootstrap/session HMAC authority |
| `gateway/server.py` | `b434cdbe118ecea48029adcd2c954fa1ac14461c` | Separate HTTP gateway server |
| `gateway/runtime_adapter.py` | `6661fbc150c77ba79d3b1f16cc0f66742b20f935` | Authenticated browser request to OperationalNORYXRuntime |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` | Action reservation, dispatch, attestation and commit sequence |
| `noryx7_runtime/state.py` | `444aba1fb92a4bb70ee2ee31b23d3946680bb630` | In-memory attestation journal and pre-dispatch reservations |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite journal for verified NORYXState commits |
| `core/state.py` | `f1dd791359038d799a63852ea850ce7f3d738148` | StateStore with optional SQLite-backed commit journal |
| `noryx7_runtime/lifecycle.py` | `71d1079f0cf1aa9cd70a097ad2a9e6365dce38b5` | Six-state execution lifecycle |
| `noryx7_runtime/scheduler.py` | `5d87d38e17c93dd26975119bb3af1dddd6c132b9` | Deterministic topological ordering |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` | Local provider registry and exception failover |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` | ProviderRouter-to-ExecutionFabric bridge |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | Separate bounded provider failover executor |
| `core/execution_fabric.py` | `fd14d2c3b1ab9fb70d500d09adfaf3e55e91b796` | Local callback authorization immediately before adapter execution |
| `core/coordination.py` | `c5743872a5b50765db04e4a42739e9ad238ad983` | Agent assignment, child tasks, ActionGate and result checks |
| `core/agent_mesh.py` | `25c9162750708e53742862f9f413fdf5200ca08f` | Role-based lexical-first local agent selection |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Snapshot admission and in-memory encrypted sync queue |
| `ecosystem/runtime_dispatch.py` | `9f4f628c322aabb571fce64d54c3d6740cb142fd` | Cross-front dispatch and receipt creation |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` | Digest-bound dispatch receipt |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` | In-memory global memory and identity/authorization indexes |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` | In-memory global placement and capacity primitives |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` | Task/output/result verification contracts |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` | Deterministic generated evaluation and holdout manifest |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` | Synthetic-only cyber simulation |
| `core/resource_router.py` | `4f7bf28200edd05f1236d9779437e4aa43bba8ab` | Device/edge/cloud heuristic tier selection |

## 3. Critical collision A — two different StateJournal authorities

There are at least two distinct classes named `StateJournal` in separate packages:

### A. `noryx7_runtime.state.StateJournal`
- In-memory collections for journal entries, keys, principal bindings and step reservations.
- Reserves `(execution_id, step_id)` before dispatch.
- Can validate signed attestations and trusted agent identity.
- `noryx7_runtime.engine.RuntimeEngine` imports this class directly.
- The inspected implementation has no SQLite path or persistent storage adapter in this class.

### B. `core.state_journal.StateJournal`
- SQLite-backed `state_commits` table, WAL and `synchronous=FULL`.
- Stores canonical `NORYXState` snapshots and identity metadata.
- Enforces unique execution IDs, ordered sequence recovery and SHA-256 record-integrity checking.
- Is optionally used by `core.state.StateStore`.

These are not interchangeable implementations of one journal contract. One is an in-memory execution attestation/reservation journal; the other is a durable verified-state commit journal. The source inspected does not establish a single adapter, transaction boundary or recovery coordinator joining them.

**Architecture requirement:** rename the logical concepts in the canonical model (for example, ActionReservation/AttestationJournal versus VerifiedStateCommitStore) while preserving source compatibility until a later implementation phase. Define one operation ID namespace and explicit correlation between action reservation, attestation append, state commit, memory commit and external-effect receipt. A successful append to either journal must never be described as a global transaction.

## 4. Critical collision B — execution lifecycle cannot express effect uncertainty

`noryx7_runtime.lifecycle.ExecutionStatus` contains CREATED, RUNNING, SUCCEEDED, REJECTED, FAILED and CANCELLED. All terminal states have no outgoing transition.

In `RuntimeEngine.execute`:
1. a step reservation is made before dispatch;
2. the adapter/executor is called;
3. output verification and attestation occur;
4. the attestation journal is appended;
5. an optional committer is called;
6. exceptions return FAILED, and the reservation is intentionally retained after the side-effect boundary.

This is a deliberate replay barrier, but the lifecycle cannot distinguish “failed before dispatch” from “dispatch may have succeeded but response/commit failed”. Retaining the reservation blocks blind re-dispatch, yet no durable, target-aware reconciliation state is expressed by the six-state lifecycle.

**Architecture requirement:** keep execution lifecycle separate from effect lifecycle. Model at least dispatch-not-started, dispatch-unknown, target-accepted, effect-observed, receipt-verified, result-admitted, state-committed, compensation-required and manual-reconciliation states. A terminal execution result may coexist with an unresolved effect state; do not collapse them into one enum.

## 5. Critical collision C — API ingress is not yet one canonical route boundary

In `web/app.py`:
- `POST /v1/session` issues a gateway session using the bootstrap/session authority.
- `POST /v1/execute` requires a Bearer token and delegates to `NoryxGateway.execute`, which verifies the session before invoking RuntimeAdapter.
- `POST /api/chat` constructs a TaskSpec and invokes `get_runtime().run_hypersynth(task)` directly; the route body does not invoke the gateway session verifier.

This is a source-level difference in route-local authentication. It does not prove that the deployed endpoint is externally reachable without authentication: an upstream proxy, middleware or platform rule may protect it, but those deployment controls were not established by this route inspection.

The repository also has `gateway/server.py`, a separate HTTP server with its own route handler for `/v1/session` and `/v1/execute`. This creates two server surfaces whose deployment and route equivalence must be inventoried.

**Architecture requirement:** all ingress paths must either converge on one authenticated request-envelope boundary or document and prove an equivalent upstream trust contract. Specify header trust/stripping, principal issuer, tenant, session/device/workload binding, policy epoch, request correlation, rate/budget limits and audit event. Health routes must not accidentally become execution entrypoints.

## 6. Critical collision D — provider execution and failover have multiple paths

The inspected code exposes three separate patterns:
- `ProviderRouter.execute`: loops through matching providers and retries after generic exceptions.
- `ProviderExecutionGateway.execute`: resolves one provider, constructs an ExecutionFabric adapter and invokes it after a callback authorization check; it does not use the router's `execute` failover method.
- `ResilientProviderExecutor.execute`: implements a separate bounded retry/failover loop with its own action ID and attempt records.

The callback passed to ExecutionFabric is a local authorization hook, not by itself a durable policy decision receipt. Generic exceptions in failover do not classify whether a remote provider committed an effect before the connection failed. The action ID used by ResilientProviderExecutor is generated from principal/provider/capability/attempt ordinal, not a caller-supplied durable logical operation and remote idempotency key.

**Architecture requirement:** one canonical provider-dispatch coordinator owns retry. Provider discovery returns candidates only. The coordinator owns operation ID, attempt ID, target idempotency key, policy epoch, budget, deadline, receipt, uncertainty classification and recovery. Each adapter must declare read-only/idempotent/non-idempotent semantics and remote status-query support. No automatic failover after an indeterminate non-idempotent effect.

## 7. Critical collision E — agent identity, assignment, execution and consensus

The inspected source shows:
- `AgentMesh.route` selects the lexicographically first matching role; this is deterministic selection, not competence qualification or load/capacity-aware scheduling.
- `AgentCoordinator.assign` selects at most `max_agents` plan steps using `plan.steps[:max_agents]`; it does not assign every plan step when the plan is longer.
- `AgentCoordinator.execute` generates a new execution ID internally, then creates child TaskSpecs using each step ID as child task ID and executes assignments in a sequential loop.
- The `verify_consensus` method requires all result task IDs to be identical, while step decomposition naturally creates different child task IDs. These appear to be different aggregation semantics and need explicit separation: same-task multi-agent consensus versus multi-step task aggregation.
- `AgentCoordinator` rechecks the selected agent's trust after execution and validates child result identity, which is a useful local control.

**Architecture requirement:** distinguish plan step, child task, agent assignment, agent invocation, replica/vote and parent execution identifiers. Define a complete-plan coverage invariant, bounded parallelism, fairness/capacity, delegation lease, revocation check, cancellation and result join. Consensus must compare only outputs that share the same semantic question/claim and evidence scope; multi-step aggregation must preserve dependency structure rather than require identical child task IDs.

## 8. Critical collision F — offline outbox, snapshot authority and durability

`core.offline.py` has useful controls: authenticated snapshot callback, integrity digest, freshness bound, principal/capability checks, policy callback, recovery epoch guard, encrypted payload, and explicit reconnect authentication/channel checks.

However, the inspected queue is an in-memory dictionary, not a durable outbox. The monotonic anchor is optional. On an exception during offline execution/verification/commit, the implementation acknowledges/removes the queued execution and sets the offline state to RECOVERY. If the local execution boundary can have an effect before the exception, the queue removal does not itself reconcile that effect. Remote acknowledgement compares the supplied remote state version to the execution's base state version; the meaning of a successful state advance needs an explicit version/merge contract.

**Architecture requirement:** durable outbox/inbox, single-use snapshot epoch, revocation freshness policy, trusted clock/monotonic anchor requirements, local effect idempotency, commit receipt, conflict resolution and explicit pending/indeterminate state. Queue deletion must follow a verified durable acknowledgement, not merely a local callback return. Define which actions are forbidden offline and what can be safely deferred.

## 9. Critical collision G — dispatch receipt is not effect proof

`ecosystem.runtime_dispatch.dispatch` authorizes a principal and checks front topology, invokes a handler and then creates a `DispatchReceipt`. The receipt binds intent/source/target/execution/principal, accepted boolean, reason and evidence digest.

The inspected call builds evidence from `repr(type(value))` on success or exception type on failure. This is a structural dispatch receipt, not a digest of the actual output payload, remote target receipt or independently observed effect. A handler exception can occur after an external side effect; `accepted=False` therefore cannot be universally interpreted as “no effect occurred”.

**Architecture requirement:** preserve dispatch acceptance as its own fact and add separately typed output/effect receipts, source provenance, target operation ID, observation evidence and commit acknowledgement. The evidence digest must name exactly what bytes were hashed and who produced/verified them.

## 10. Global memory, placement and ecosystem scope — W03/W05/W08/W11/W12

- `ecosystem.global_fabric.GlobalMemoryFabric` is an in-memory index of record IDs, levels, versions, payload/provenance digests and replica IDs. Its own module states encryption, durable storage and transport are adapters.
- `GlobalIdentityAuthorizationFabric` is a local identity/session/device/capability index; it is not automatically the same authority as the local gateway SessionAuthority, core IdentityRegistry or runtime agent identity registry.
- `ecosystem.global_scale.GlobalControlPlane`, `CellRegistry` and `ElasticComputeFabric` model region/cell/worker-pool selection and capacity accounting in process. The module explicitly requires production adapters for real infrastructure.
- `core.resource_router.ResourceRouter` selects device/edge/cloud from complexity, privacy and latency heuristics. It is not a placement lease, reservation or scheduler.
- W12 business/community and financial-ledger architecture remains a distinct domain. This source pass did not establish a complete production financial ledger or independently audited impact pipeline; no absence claim is made from the bounded paths inspected.

**Architecture requirement:** establish a canonical registry/authority hierarchy and adapter contracts for durable distributed state, key custody, placement leases, capacity reservation, billing, financial segregation and independent impact evidence. Business/financial records must not issue runtime capabilities.

## 11. W01–W12 impact and dependency matrix

| Workstream | Source-level conflict or missing contract | Required upstream relationship |
|---|---|---|
| W01 Identity/authority | Gateway sessions, core agent identity, runtime identity registry and global identity index are separate local abstractions | Canonical principal and issuer/epoch model before dispatch |
| W02 Runtime | FastAPI direct route, gateway adapter, standalone gateway server and RuntimeEngine are distinct entrypoints | W01 ingress; W03 effect/state lifecycle |
| W03 Memory/state | Two StateJournal classes, separate StateStore and runtime journal; global memory index is in-memory | W01 identity; W02 lifecycle; W06 provenance |
| W04 Agents | AgentMesh lexical role choice, AgentCoordinator truncation/sequential execution and two result aggregation semantics | W01 delegation; W02 parent execution; W05 scheduling |
| W05 Routing | ProviderRouter, ProviderExecutionGateway, ResilientProviderExecutor and ResourceRouter overlap | W01 authorization; W02 coordinator; W03 idempotency |
| W06 NEXUS/evidence | Dispatch receipt, attestation, verification result and evaluation result represent different evidence types | W01 issuer; W03 durable custody; W07 simulation evidence |
| W07 MIRROR WORLD | CyberRange report `verified=True` is bounded synthetic simulation completion | W06 evidence class; W09 authorization boundary |
| W08 Browser/device/offline | FastAPI and standalone gateway surfaces; in-memory offline queue; optional monotonic anchor | W01 principal; W02 execution; W03 durable outbox |
| W09 Security/recovery | Local recovery epoch, replay guard, gateway HMAC session and agent registry do not establish fleet-wide revocation | W01 canonical identity; W03 durable state |
| W10 Specialists | Role/skill routing does not prove qualification, scope, jurisdiction or independent competence | W06 evidence; W09 authority; W05 eligibility |
| W11 Operations | In-memory capacity/placement primitives and separate release surfaces need operational adapters/evidence | W05 budgets; W08 fleet; W09 assurance |
| W12 Economy/community | Financial custody and impact verification remain separate from runtime/global registries | W06 outcome evidence; W09 governance; W11 metering |

## 12. Required canonical object model before freeze

The architecture must define and version distinct objects, even if a later implementation chooses to combine their storage:
1. `PrincipalAssertion` — issuer, subject, tenant, device/workload, assurance, policy epoch, expiry and revocation state.
2. `ParentExecution` — request, plan digest, caller, deadline, cancellation and budget.
3. `StepInvocation` — step, dependencies, assigned agent, attempt and delegation lease.
4. `ActionAuthorization` — exact action/target/payload digest, capability, policy decision and replay identity.
5. `DispatchAttempt` — adapter/provider, request ID, idempotency key, dispatch timestamp and transport result.
6. `EffectReceipt` — target operation ID, accepted/observed/unknown state, evidence and verifier.
7. `AttestationRecord` — signer identity, key epoch, execution/action/output digests and predecessor.
8. `StateCommit` — authoritative state version, principal, verification stage and durable transaction result.
9. `MemoryRecord` — tenant/scope, content digest, provenance, retention/deletion tombstone and replica custody.
10. `ReleaseEvidence` — artifact digest, source revision, build/test/sign/promotion/rollback record and environment.
11. `DomainQualification` — competence evidence, jurisdiction, scope, expiry, conflict and suspension.
12. `FinancialEntry` / `ImpactEvidence` — segregated accounting, independent verifier, baseline/counterfactual, uncertainty and appeal.

These objects must have explicit owner, writer, reader, persistence, integrity/authenticity, lifecycle, deletion, recovery and cross-boundary rules. A shared identifier string does not imply a shared authority.

## 13. Architecture closure disposition

- The source confirms several valuable local fail-closed mechanisms; this document does not dismiss or replace them.
- The source also confirms multiple local journals, registries, routers, lifecycle enums and dispatch surfaces whose system-wide coordination is not yet demonstrated.
- ADR-002 through ADR-005 remain proposed pending ownership and call-path evidence.
- Existing ADR-B56–B62 and the identity/state/memory/routing/evidence decisions remain OPEN where their acceptance evidence is missing.
- W01–W12 remain PARTIAL. No workstream is promoted to DECIDED or FROZEN.
- Next source pass: map all construction/registration/call sites for both journals, all gateway/FastAPI deployment ingress, all provider retry callers, all AgentCoordinator/AgentMesh consumers, offline queue persistence adapters, and W12 ledger/impact source paths.
- No implementation, integration, test campaign, merge or deployment is authorized by this document.
