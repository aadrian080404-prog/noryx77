# NORYX7 — Parallel Closure Acceleration, Dependency DAG and Integration Readiness

**Inspection ref:** `9717088d23b36ee2b4fe70addf0bb2fc153a377e`  
**Phase:** architecture-only; no implementation, runtime, test, dependency, workflow, deployment or configuration changes authorized.  
**Purpose:** accelerate W01–W12 closure by parallelizing bounded work, avoiding repeated discovery, and preparing a deterministic integration sequence without starting integration prematurely.

## 1. Governing rule

Acceleration changes coordination and evidence reuse, not the safety bar. A source file, passing structural gate, CI workflow or architecture document is not by itself proof of end-to-end behavior. No workstream is FROZEN, IMPLEMENTED or VERIFIED solely because its documentation exists.

The existing branch remains a draft architecture branch. The frozen baseline is not modified. This document does not authorize merge, runtime changes, test campaigns or deployment.

## 2. Current executable-path observations

The following source anchors were inspected at the inspection ref:

| Source | Blob SHA | Bounded observation | Not established by this source alone |
|---|---|---|---|
| `gateway/server.py` | `b434cdbe118ecea48029adcd2c954fa1ac14461c` | Gateway owns session issue/verification and delegates execute to RuntimeAdapter. | TLS termination, production secret custody, distributed session/revocation behavior. |
| `gateway/runtime_adapter.py` | `6661fbc150c77ba79d3b1f16cc0f66742b20f935` | Authenticated client request becomes TaskSpec; adapter calls HYPERSYNTH, rejects non-completed or invalid verification results. | Parity with every other ingress route and durable principal/tenant binding across all stores. |
| `core/operational_runtime.py` | `0106879b43b8de90a87a11ca9c361be72ab37072` | OperationalNORYXRuntime requires ModelFabric, starts required Primary/Secondary agents and checks online/fabric registration. | External provider availability, multi-process coordination, persistent agent registry or independent semantic truth. |
| `noryx7_operational.py` | `72300445c4c3cb8e18ae94f0226c2246a069d368` | Operational CLI requires OPENROUTER_API_KEY, builds OpenRouter ModelFabric, optionally configures SQLite journal path, and runs tasks. | That the hosted gateway deployment uses the same composition or has a durable journal configured. |
| `core/runtime.py` | `454f90e6b06ca6f013e325640a16d349b18797ae` | NORYXRuntime composes policy, recovery, security, ActionGate, memory, state, optional journal, routing and HYPERSYNTH. | That every runtime facade delegates to this exact instance or that every persistence namespace shares one recovery protocol. |
| `core/system_fabric.py` | `cf28bd8a144480467b6bd2cf3726b510a7b7924f` | CanonicalSystemFabric checks identity equality for runtime engine, executor, verifier, authorization, principal and policy. | Universal adoption by every ingress/provider/JARVIS path. |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` | ProviderExecutionGateway authorizes provider dispatch through ExecutionFabric. | That it is the only provider execution path. |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | ResilientProviderExecutor has bounded attempts and failover. | Safe retry after ambiguous external side effects, common idempotency key or reconciliation with other provider gateway. |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite WAL/FULL append-only verified-state journal with digest and schema version. | Journal configured in every deployment, cross-journal atomicity, backup/restore or external effect saga. |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Offline lifecycle includes disconnected, sync-pending, conflict, reconnecting and recovery states; bounded encrypted queue contracts. | Durable queue/inbox/ack and globally coordinated replay protection. |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` | Validates task contract and presence/shape/identity of outputs and agent result sets. | Semantic truth, domain correctness or external-effect completion. |
| `ecosystem/global_closure.py` | `d4f84e5cb23a764c1a85527fb0cf101ebaf11457` | Imports required modules/symbols and checks structural seams; explicitly leaves external KMS/HSM, hardware counters, devices and CI as external boundaries. | Production behavior, hardware trust, real distributed operation or semantic correctness. |
| `ecosystem/completeness.py` | `c4fb481703c6c2059d1cfea08a24300e7277f270` | Combines contract shape, canonical plane gate, structural paths and browser source-isolation scan. | Runtime sandboxing, universal egress mediation or full operational completeness. |

### Key integration-readiness conclusion

There is already a usable vertical slice in source, but there are multiple adjacent execution and state abstractions. The acceleration bottleneck is not simply missing code: it is proving one canonical composition and eliminating or explicitly adapting parallel authorities. The first integration target should be one thin, demonstrable vertical slice, not simultaneous rewrites of all subsystems.

## 3. Acceleration mechanism: one inventory, many bounded lanes

Each workstream uses the same evidence card:

- **Owner:** one canonical owner for each responsibility.
- **Source scope:** exact inspected paths and commit/blob SHAs.
- **Contract:** typed inputs, outputs, identity, state and error semantics.
- **Dependencies:** upstream contract IDs; no implicit dependency.
- **Lifecycle:** create, authorize, execute, verify, commit, cancel, expire, recover and delete where applicable.
- **Threat boundary:** trust assumptions, abuse cases, fail-closed behavior and human control.
- **Acceptance evidence:** specific test/experiment/operational evidence required later.
- **Disposition:** DECIDED, DEFERRED with owner/reason, or OPEN.

A source change invalidates only the evidence cards that depend on that path or contract. Unchanged source evidence is reused with its original inspection ref; it is not silently promoted to current implementation proof.

## 4. Parallel workstream lanes and dependencies

| Lane | Scope | Can progress concurrently on | Must wait for |
|---|---|---|---|
| W01 Authority & identity | principal/session/tenant, trust roots, capabilities, ActionGate, revocation | issuer/consumer inventory, trust-zone matrix, offline authority options | Canonical principal and grant contract before dependent freeze |
| W02 Runtime topology | ingress, runtime facades, HYPERSYNTH, JARVIS, lifecycle | constructor/call-site inventory and facade ownership matrix | W01 authority and W03 state ownership |
| W03 State & recovery | memory, journals, attestation, checkpoints, offline reconciliation | persistence namespace and recovery-consumer inventory | W01 identity plus W02 execution lifecycle |
| W04 Agent fabric | native/operational/JARVIS agents, delegation, supervision, result admission | direct invocation inventory, lifecycle and result-envelope comparison | W01 identity and W02 runtime envelope |
| W05 Routing & resources | model/provider routing, agent selection, scheduler, placement, budgets | router inventory, retry nesting, budget ownership | W02 execution envelope and W04 delegation |
| W06 Semantics & evidence | NEXUS, claims, evidence, FRL, research, provenance | source-to-claim schema, epistemic state model, lineage | W01 principal and W03 durable evidence/state |
| W07 MIRROR WORLD | world graph, kernels, simulation, cyber range, Reality Bridge | model inventory, fidelity labels, experiment manifest | W01 authorization, W03 state and W06 evidence |
| W08 Surfaces & distribution | gateway, browser, JARVIS, terminal, mobile, edge/cloud/offline | route parity, surface capability manifests, transport matrix | W01/W02 identity and runtime contracts |
| W09 Security & assurance | keys, crypto, egress, audit, privacy, supply chain, incident response | trust-zone and enforcement coverage inventory | W01/W03 canonical authority and state |
| W10 Domain fabrics | health, legal, finance, science, engineering, environment, agriculture, education | domain manifest template, expert/reviewer and source-class requirements | W06 evidence and W09 safety |
| W11 Performance & operations | budgets, SLOs, telemetry, capacity, fairness, service continuity | measurement definitions, capacity assumptions, queue/backpressure inventory | W05 routing/resource ownership and W08 surfaces |
| W12 Product & ecosystem | marketplace, billing, ledger, community, environmental impact | product boundary, money-flow and impact-evidence inventories | W06 evidence, W09 controls, W10 domain governance, W11 operations |

**Parallelism rule:** all lanes can inspect, specify and record alternatives concurrently. Decisions that change shared identity, runtime, state, action, evidence or wire contracts are serialized through one decision owner and one ADR. No concurrent code changes are part of this phase.

## 5. Dependency DAG for closure and later integration

The closure order is a partial order, not twelve sequential projects:

1. **Shared substrate decisions (blocking):** W01 authority/principal; W02 runtime ownership; W03 state/effect/recovery; W04 agent identity/delegation; W06 evidence envelope.
2. **Parallel dependent decisions:** W05 routing/resource ownership; W07 simulation and Reality Bridge; W08 surfaces/distribution; W09 trust/assurance; W10 domain manifests; W11 operations; W12 ecosystem/ledger.
3. **Global consistency pass:** contract versions, state machines, error outcomes, ownership, terminology, threat model, migration/deprecation and unresolved-decision ownership.
4. **Architecture freeze manifest:** exact accepted ADRs, deferred items, source refs, contract versions, excluded work and approvers.
5. **Only after freeze:** implement one vertical slice and its compatibility adapters; then expand by dependency group.
6. **Only after integration:** run comprehensive unit, integration, adversarial, recovery, performance, device and end-to-end campaigns.

This allows work in W05–W12 to progress while W01–W06 are being reconciled, but prevents dependent decisions from being falsely frozen against unstable contracts.

## 6. First vertical slice proposed for post-freeze integration

The minimum useful proof should be a single authenticated task through one selected production composition:

`Client -> Gateway Session -> RuntimeAdapter -> Canonical Runtime -> HYPERSYNTH -> Primary/Secondary -> Authorized Capability -> Verification -> State Commit -> Audit/Response`

Acceptance must prove, on one recorded build/configuration:

1. principal and execution identity are stable end-to-end;
2. every side effect crosses one explicit authorization boundary;
3. provider retries cannot duplicate an ambiguous non-idempotent effect;
4. result admission checks identity, provenance and task coverage;
5. durable state commit and recovery behavior are demonstrated;
6. denial, timeout, cancellation, partial result and uncertain effect have distinct outcomes;
7. audit evidence can reconstruct the lifecycle;
8. no alternate ingress silently bypasses the canonical path.

This is a proposed integration target, not a claim that all eight properties are already satisfied.

## 7. Evidence levels and state transitions

Use these exact meanings:

- **DISCOVERED:** symbol/path/behavior found at a named source ref.
- **SOURCE-RECONCILED:** callers, owners and limitations inspected for a bounded scope.
- **SPECIFIED:** normative contract and failure semantics written.
- **DECIDED:** accepted ADR with alternatives and consequences.
- **FROZEN:** contract included in an approved architecture freeze manifest.
- **IMPLEMENTED:** code is traceable to that frozen contract.
- **INTEGRATION-VERIFIED:** contract tested across its declared component boundary.
- **OPERATIONALLY-VERIFIED:** observed in a named environment/configuration with reproducible evidence.

No automatic promotion is allowed. CI success only supports the exact jobs and commit that ran. Structural gates prove structural properties only.

## 8. Immediate parallel tasks for the next cycles

- W01/W02: finish full ingress and constructor/call-site graph, including all API routes, CLI and JARVIS.
- W03/W09: enumerate every persistent store, journal, queue, key provider, anchor and recovery consumer; classify durable versus process-local.
- W04/W05: enumerate direct agent/provider invocations, retry nesting, idempotency and resource admission.
- W06: define canonical Claim/Evidence/SourceArtifact/VerificationRecord and correction/retraction/expiry lifecycle.
- W07/W10: inventory actual implemented model kernels separately from architecture-only environmental, physical and socio-economic models.
- W08/W11: map browser/mobile/edge/cloud surfaces to ingress, identity, network egress, telemetry and service objectives.
- W12: separate product concepts from executable payment, ledger, escrow, marketplace and independently measured impact capabilities.
- Cross-cutting: run a documentation consistency audit for duplicate IDs, conflicting schemas, ownership collisions and unresolved ADRs.

## 9. Current disposition

All W01–W12 remain **PARTIAL**. ADR-001 through ADR-005 and the B-series decisions remain subject to their documented acceptance evidence. The source inventory shows meaningful executable foundations, including an authenticated gateway path, an operational Primary/Secondary composition, ActionGate/verification components and an optional durable SQLite journal. It does not establish a unified production composition, complete persistence/recovery, full egress enforcement, semantic verification or global federation.

**No architecture freeze is declared. No integration, comprehensive test campaign, merge or deployment is claimed or authorized by this document.**
