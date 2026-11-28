# NORYX7 — Source reconciliation findings: W01–W05

**Inspected source ref:** main at 7d900bc75843ea968aa5886d251dbfac83a5d93c  
**Status:** partial source reconciliation; architecture-only; findings are bounded to the inspected files  
**Purpose:** convert direct source inspection into explicit architecture questions without treating one file as the whole system.

## 1. W01 — Identity, policy and authority

| Source | Directly observed contract | Architectural implication |
|---|---|---|
| core/identity.py | AgentIdentity and AgentAttestation use Ed25519; IdentityRegistry stores agent ID → public key in an in-memory dictionary guarded by RLock; register rejects duplicate IDs; revoke removes the key; with_trusted_identity provides a short locked callback | This is a local in-memory trust registry. It does not alone define durable principal identity, device identity, tenant identity, trust-root enrollment, federation or recovery. Reconcile with durable identity/binding registries elsewhere in the repository. |
| core/policy.py | PolicyEngine uses a fixed ALLOWED_ACTIONS set and HIGH_RISK set; malformed/unknown actions deny; high-risk or requires_authorization actions deny | This is a narrow action classifier/allowlist, not a complete policy language or identity/tenant/consent decision model. Preserve fail-closed behavior while locating the actual authorization authorities and call order. |
| core/multiauth.py | AuthorizationProof is explicitly legacy structural data and not cryptographic; SignedAuthorizationProof and SignedApprovalAuthority verify Ed25519 signatures against an in-memory trusted-key map and action/epoch statement | Call sites must never treat structural proof as cryptographic approval. Trusted-key persistence, principal independence, revocation freshness and epoch authority need reconciliation. |
| core/authorization_replay.py | bounded in-memory set of consumed 32-byte tokens; maximum 4096 | Local single-process replay guard is not itself a durable or cross-host replay authority. Map durable SQLite grant/replay components and define shared namespace/consistency boundaries. |

**Open W01 questions**
- Which durable registries are canonical for human principals, agent identities, devices and principal-agent bindings?
- Who issues and rotates trust roots and who can revoke each identity class?
- What is the single policy epoch authority? How do revocation, expiry and offline leases interact?
- Which authorization proof type is accepted at each ActionGate boundary?
- How are independently controlled approvers established and how is independence evidenced?
- How does bootstrap recover from lost/corrupt trust roots without an agent-created bypass?

## 2. W02 — Runtime topology

| Source | Directly observed contract | Architectural implication |
|---|---|---|
| core/runtime.py | NORYXRuntime owns run, run_hypersynth, offline configuration/snapshot and execution path; constructor accepts journal path and model fabric among other dependencies | This is a broad runtime facade with multiple modes. Map all constructor wiring, route callers, lifecycle and compatibility users before making it canonical. |
| core/hypersynth_runtime.py | HypersynthRuntime independently owns verifier, router, planner, audit, limits, memory, clock, recovery and PolicyEngine; has its own run path and collaboration helper | This is a second runtime facade with overlapping safety dependencies and task execution responsibilities. |
| core/operational_runtime.py | OperationalNORYXRuntime subclasses NORYXRuntime and declares required agent IDs plus heartbeat/shutdown | Operational runtime adds service lifecycle around a base runtime, but the relation to HypersynthRuntime and noryx7_runtime/engine remains to be made explicit. |

**Open W02 questions**
- Which runtime owns process startup/shutdown, admission, deadlines, cancellation, state commit and recovery?
- Is HYPERSYNTH a cognitive subsystem invoked by NORYXRuntime, a runtime facade, or both depending on entrypoint?
- Which constructors are production entrypoints versus tests, compatibility facades or local demos?
- How do JARVIS, API, offline and operational modes enter the canonical runtime?
- What is the migration/deprecation path for duplicate facades?

## 3. W03 — State and journal

| Source | Directly observed contract | Architectural implication |
|---|---|---|
| core/state.py | StateStore optionally receives StateJournal; commit requires verification_valid=True, verification_stage=runtime_result, input digest, no raw user_input, principal ID and key fingerprint; execution IDs are unique within store | Strong local commit preconditions exist. Clarify which verifier is authoritative, how principal binding is rechecked at commit, and how stores share execution namespaces. |
| core/state_journal.py | SQLite WAL, synchronous=FULL, append-only state_commits table, schema version 1, unique execution ID/sequence, SHA-256 digest of canonical row, recovery checks contiguous sequence and digest | This component provides a local hash-checked journal, not by itself an externally anchored hash chain, encrypted store, multi-host consensus, backup policy or schema migration framework. Other audit journals/witnesses must be reconciled rather than assumed equivalent. |

**Open W03 questions**
- Are state commits, execution journals, audit logs, domain ledgers and external witnesses separate canonical namespaces?
- Is there one globally unique execution ID across all runtime facades and distributed nodes?
- How are journal migrations, compaction, retention, encryption, backups and restore performed?
- How does recovery handle a crash after external dispatch but before local commit?
- How are revocations and policy epochs preserved when restoring older state?
- Which commit operation is atomic with identity/revocation checks, and which checks are merely sequential?

## 4. W04 — Agent fabric and result admission

| Source | Directly observed contract | Architectural implication |
|---|---|---|
| core/agent_fabric.py | AgentFabric stores AgentBinding objects in an in-memory map; validates skills and trusted identity; checks principal context spoofing; invokes binding.agent.run directly after callback authorization | This is a native local dispatch path. It is distinct from the operational fabric and must be classified as canonical, adapter, legacy or test-only. |
| core/operational_fabric.py | OperationalAgentFabric wraps AgentSupervisor and ResourceRouter; selects, dispatches, admits results and records optional audit events | This is a second orchestration path with explicit task verification and result admission. |
| core/supervisor.py | AgentSupervisor verifies tasks before selection and validates result contracts during admission | The exact trust binding, selected-agent binding and post-execution state commit relationship must be traced end to end. |

**Open W04 questions**
- Can any production call site invoke AgentCore.run without the canonical supervisor/admission pipeline?
- Are AgentIdentity and durable principal-agent binding checked at dispatch and held valid across the full action boundary?
- How do native and operational fabrics share skill manifests, identity lifecycle, leases, cancellation and resource accounting?
- Is result admission independent from the executing agent and its provider?
- How are timeouts, retries, partial results, duplicate delivery and uncertain side effects represented?

## 5. W05 — Provider routing, agent allocation and resource placement

| Source | Directly observed contract | Architectural implication |
|---|---|---|
| core/router.py | ResourceRouter registers agent objects and routes by preferred/default ID; can check agent identity trust | Despite its name, this is primarily an agent registry/selector, not device/edge/cloud placement. |
| core/resource_router.py | ResourceRouter chooses DEVICE/EDGE/CLOUD using only complexity, privacy_required and latency_sensitive | This is a deterministic tier heuristic. It does not itself encode live capacity, cost, residency, hardware, energy, deadline, trust posture or failure-domain constraints. |
| core/provider_router.py | ProviderRouter selects the first registered provider matching a capability; execute catches provider exceptions and tries another provider until exhausted | Provider order is observable policy. Failover must be reconciled with idempotency, side effects, data residency, tenant isolation, provider trust and cost. |
| core/provider_execution.py | ProviderExecutionGateway bridges ProviderRouter to ExecutionFabric and provides per-call authorization | Map this gateway against provider routing and execution fabric so authorization is not duplicated or bypassed. |
| core/provider_resilience.py | ResilientProviderExecutor adds bounded attempts and records attempt results | Reconcile retry limits and failure classifications with ProviderRouter failover to avoid nested/unbounded retries or duplicate external effects. |

**Open W05 questions**
- What is the canonical distinction among model/provider selection, agent selection, task scheduling, node placement and tool dispatch?
- Which component owns capacity reservation and releases it on cancellation/failure?
- Which constraints are hard admission rules versus ranking preferences?
- How are retry budgets composed across gateway, provider router, resilience layer and runtime?
- What prevents failover from forwarding sensitive context to a provider outside the permitted region or trust profile?
- How are billing/metering and per-tenant fairness bound to actual resource consumption?

## 6. Consolidated source-grounded findings

1. Several local in-memory authorities coexist with durable identity/replay work elsewhere. They must not be treated as equivalent trust domains.
2. NORYXRuntime, HypersynthRuntime and OperationalNORYXRuntime overlap in runtime responsibility; the canonical entrypoint and facade direction are not yet proven.
3. StateStore and StateJournal have clear local commit checks, but their relationship to audit journals, external anchors, distributed recovery and domain state is not fully specified.
4. AgentFabric and OperationalAgentFabric expose distinct dispatch paths. The production call-site graph is needed before choosing one canonical path.
5. Router names conceal different responsibilities: agent selection, provider selection and compute-tier placement are separate decisions.
6. Provider failover and retry layers need a single composed idempotency and side-effect policy.
7. Existing cryptographic primitives and local guards must be joined to key custody, durable identity, policy epochs, offline freshness and recovery contracts.

## 7. Decisions to add to the backlog

- Identity and trust-root authority: durable owner, bootstrap, rotation, revocation, offline freshness and recovery.
- Runtime facade ownership: canonical coordinator, entrypoints, adapters, migration and lifecycle.
- State namespace/recovery ownership: execution state, audit, domain ledger, external witness and saga/compensation boundaries.
- Agent dispatch ownership: native/operational fabric classification and mandatory result admission.
- Routing/resource ownership: provider, agent, scheduler, placement, dispatch, retry and budget boundaries.

## 8. Scope and next step

Inspected files: core/identity.py, core/policy.py, core/multiauth.py, core/authorization_replay.py, core/runtime.py, core/hypersynth_runtime.py, core/operational_runtime.py, core/state.py, core/state_journal.py, core/agent_fabric.py, core/operational_fabric.py, core/supervisor.py, core/router.py, core/resource_router.py, core/provider_router.py, core/provider_execution.py and core/provider_resilience.py.

This is a bounded source review, not an exhaustive repository call-site audit. Next pass must trace all constructors and callers, inspect durable identity/binding registries, map all journals and recovery consumers, and inspect JARVIS/noryx7_runtime entrypoints. No code, tests, integration or deployment are changed by this document.
