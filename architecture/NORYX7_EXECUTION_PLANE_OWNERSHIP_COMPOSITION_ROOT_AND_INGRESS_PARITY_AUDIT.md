# NORYX7 — Execution Plane Ownership, Composition Root and Ingress Parity Audit

**Review date:** 2026-11-28  
**Source-tree HEAD inspected:** `3045257dbce31c901dbac48077ce505908a21af4`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Mode:** architecture-only source audit and proposed ownership contract. No runtime, API, browser, test, dependency, workflow, deployment, frozen baseline or production configuration changed.

## 1. Executive finding

The repository contains multiple real execution subsystems, but the inspected composition roots do not demonstrate one end-to-end operational authority shared by every front door.

Three distinct paths are visible:
1. FastAPI composes `OperationalNORYXRuntime`, `OperationalAgentFabric`, HYPERSYNTH and ModelFabric.
2. JARVIS composes a separate `JarvisRuntime`, `CanonicalSystemFabric`, `JarvisRuntimeBridge`, `RuntimeEngine`, `ToolExecutor` and its own user-level policy/state/recovery.
3. Go and Rust service stubs expose small health/digest or serialization helpers, not an interoperable runtime protocol or shared remote execution authority.

JARVIS `CanonicalSystemFabric` enforces object identity among components passed to its bridge. That is a useful local consistency check; it does not prove that web/HYPERSYNTH ingress uses those same objects. Conversely, operational HYPERSYNTH has an `OperationalAgentFabric`, but it is not shown as the same execution engine or state journal as JARVIS RuntimeEngine.

The gap is the absence of an accepted system-wide ownership map and enforceable composition contract: which plane owns each operation, which components are shared, which are adapters, which state is authoritative, and how all ingress routes inherit equivalent identity, authorization, egress, verification, audit and commit requirements. Multiple execution planes may be intentional; ambiguous ownership and hidden bypasses are not.

## 2. Bounded source observations

### 2.1 FastAPI production composition

`web/app.py` blob SHA: `a03d012d6f9f2fdbfb8a5e64397511e5ac692360`.

- `get_runtime()` constructs OpenRouterAdapter, ModelFabric and `OperationalNORYXRuntime`, optionally with a Core SQLite state-journal path.
- `get_gateway()` wraps that same cached OperationalNORYXRuntime in `RuntimeAdapter` and `NoryxGateway`.
- `/v1/session` and `/v1/execute` pass through the gateway session path.
- `/api/chat` constructs a TaskSpec and calls `runtime.run_hypersynth(task)` directly. The handler itself does not read or require the gateway Bearer session. External reverse-proxy controls are outside this source review.
- Both routes use the same cached OperationalNORYXRuntime object, but do not have the same route-level authentication path.

`gateway/runtime_adapter.py` blob SHA: `6661fbc150c77ba79d3b1f16cc0f66742b20f935` translates the session's client ID into a TaskSpec constraint. This adapter does not independently establish a device-bound principal; the prior session audit records that boundary.

### 2.2 Operational HYPERSYNTH plane

`core/operational_runtime.py` blob SHA: `0106879b43b8de90a87a11ca9c361be72ab37072`.

- Requires injected ModelFabric, initializes `NORYXRuntime`, starts primary and secondary agents, and assigns `OperationalAgentFabric` as HYPERSYNTH kernel supervisor.
- `core/operational_fabric.py` blob SHA `a2f6a46c1fdec47f3fe1f95f6c20f9848673f127` binds router, verifier and supervisor for agent selection/admission. It is not JARVIS `CanonicalSystemFabric`.
- `core/runtime.py` blob SHA `454f90e6b06ca6f013e325640a16d349b18797ae` constructs `HypersynthRuntime`, Core StateStore and optional Core SQLite StateJournal. It does not construct JARVIS `noryx7_runtime.engine.RuntimeEngine` as its main execution engine.
- This operational path has its own lifecycle, memory, audit, recovery and state composition. Its relationship to JARVIS RuntimeEngine and commit semantics must be normative.

### 2.3 JARVIS plane and canonical fabric

`jarvis/core/runtime.py` blob SHA: `09134dbd587b118f43dfbd07a6c054eddedd1cc8`.

- Constructs its own VerificationEngine, PolicyEngine, SecurityBoundary, IdentityRegistry, AgentIdentity, AuthorizationAuthority, ActionGate, ToolExecutor, RuntimeEngine, provider gateway/resilience executor, JARVIS state store, recovery controller and execution trace map.
- Creates `CanonicalSystemFabric` from the exact JARVIS RuntimeEngine, ToolExecutor, verifier, authorization authority, JARVIS identity and orchestrator policy.
- `core/jarvis_runtime_bridge.py` blob SHA `0f5611bdccfa917c601a34b471c198a65fcbd48c` asserts those exact object identities and translates JARVIS PlanSteps into RuntimeEngine steps. It invokes ToolExecutor and checks output presence/shape.
- JARVIS performs user-level policy authorization, reserves JARVIS state, invokes the bridge, verifies ActionResults and commits JARVIS state. JARVIS state and RuntimeEngine state journal are separate state owners in the inspected composition; atomic cross-store commit is not established.
- JARVIS also owns ProviderExecutionGateway and ResilientProviderExecutor, while the RuntimeEngine bridge uses ToolExecutor. Their relationship to operational runtime ModelFabric/provider path needs an explicit operation/effect contract.
- `jarvis/runtime_facade.py` blob SHA `b1a50f1c8c6566804151f81daf93114205f2afb9` creates a default JarvisRuntime and a Request with literal principal ID `user`; this facade constructor does not show caller-authenticated principal binding.

CanonicalSystemFabric is a local JARVIS bridge consistency object, not evidence that all NORYX7 surfaces share one global runtime instance.

### 2.4 Structural closure gates

- `ecosystem/global_closure.py` blob SHA `d4f84e5cb23a764c1a85527fb0cf101ebaf11457` imports required modules, checks symbols/paths and runs browser isolation scanning.
- `ecosystem/completeness.py` blob SHA `c4fb481703c6c2059d1cfea08a24300e7277f270` checks closure-contract shape, architecture registry evaluation, required paths and browser isolation.
- `ecosystem/closure_contract.py` blob SHA `c4cb5b27f0b05462f1bf7658e2a82455d49d19ac` declares required boundaries/invariants per front.
- `ecosystem/structural_manifest.py` blob SHA `2e2096d924386646582abe1a6a38488c8be6c8c3` checks expected file paths.

These gates check structural presence and browser isolation. They do not prove every production ingress uses the same composition root, that object identity is shared across fronts, that each operation has one authoritative state owner, or that cross-store effects commit atomically. Structural closure PASS must not be presented as complete operational composition assurance.

### 2.5 Polyglot services

- `services/jarvis-gateway-go/main.go` blob SHA `1d9baa84b229ad8056be69f3a0955ead3d1f981e` exposes GET /health and POST /digest over request bytes; it does not implement the authenticated gateway session or execution contract inspected in Python.
- `services/jarvis-runtime-rs/src/lib.rs` blob SHA `035960c0d08f1db5825f01a78ce314f7055516c0` defines a small ExecutionEnvelope, serializes with serde_json and computes SHA-256; it does not implement the full canonical signed operation/receipt protocol.
- `ARCHITECTURE/JARVIS_POLYGLOT.md` describes intended language ownership. The inspected Go/Rust stubs do not establish that ownership map as implemented runtime behavior.

## 3. Proposed system-wide plane ownership

Logical ownership is distinct from deployment topology. A plane may have replicas, but each logical responsibility needs one authoritative contract and explicit delegation.

| Plane | Proposed logical owner | Must not own |
|---|---|---|
| Ingress / Surface | Surface gateway; authenticates source and constructs trusted request context | Cognitive plan authority or raw external-effect commit |
| Identity / Trust | Identity and delegation authority | Task planning or result truth |
| HYPERSYNTH | Intent understanding, hypothesis/plan generation and bounded branch scheduling | Permission to execute its own proposed actions |
| Agent Fabric | Agent qualification, assignment, collaboration and result submission | Principal authentication or final state commit |
| Action / Capability Gate | Policy decision and one-shot capability consumption | Claim that an external effect succeeded |
| Execution Runtime | Operation lifecycle, attempts, scheduling and effect reconciliation | Cognitive truth or source ownership |
| Tool / Provider Fabric | External capability adapters and transport | Independent authority or blind retry after ambiguous effects |
| Verification / Evidence | Result admission, provenance, semantic checks and independent corroboration | Rewriting source evidence or self-issuing execution authority |
| Memory / State | Durable operation state, verified memory and audit checkpoints | Unverified model output as committed fact |
| NEXUS / FRL / MIRROR WORLD | Claim/evidence graph, formal proof checks, simulation and reality comparison | Permission to test or actuate real systems |
| Device / Network Fabric | Device identity, egress lease and connectivity enforcement | User identity or business authorization |
| Global Control Plane | Placement leases, fencing, regional health and failover | Replacing per-operation authorization or commit proof |
| Economy / Governance | Ledger, settlement, voting and impact records | Reinterpreting execution success as financial settlement |

This is a proposed ownership baseline, not a declaration that these logical owners already exist as one deployed service.

## 4. Required composition-root contract

Every production composition root must publish a signed/versioned CompositionManifest containing:
- composition ID/version, deployment/build digest and environment;
- ingress routes and front/surface identifiers;
- authoritative principal issuer, session audience, device/workload trust source and revocation path;
- exact runtime/execution engine and lifecycle owner;
- exact HYPERSYNTH/Agent Fabric/ToolExecutor/Provider Fabric bindings;
- policy, authorization, verifier and audit implementations with trust roots;
- state/memory/journal stores and transaction boundaries;
- egress enforcement point and network-presence lease authority;
- recovery controller, epoch source and stale-work fencing;
- cross-store commit/reconciliation protocol;
- external provider endpoints and idempotency/effect receipt contract;
- disabled capabilities and fail-closed behavior;
- health probes separately reporting structural, dependency, authorization and evidence/commit readiness.

The manifest must be checked at startup and bound to deployment attestation. Component presence in dependency injection is insufficient: every route must resolve to declared authorities, with no alternate path bypassing them.

## 5. Ingress parity contract

All ingress routes converge on one request-normalization and identity-binding boundary before reaching HYPERSYNTH or execution.

Required invariants:
1. No route accepts a caller-provided string as authenticated principal identity.
2. Surface identity, user principal, device identity, agent identity and delegated workload identity are separate fields.
3. Every request binds tenant, audience, session, policy epoch, operation ID and provenance.
4. `/api/chat`, `/v1/execute`, browser navigation, voice/wake, internal agents and external APIs receive equivalent authentication/authorization requirements for equivalent actions.
5. A route may be stricter, never weaker through hidden defaults.
6. CORS, reverse proxies, service meshes and gateway controls are documented as external enforcement layers and verified independently.
7. Health endpoints distinguish structural readiness from operational readiness.
8. Any unmanifested route, alternate runtime constructor or fallback principal causes composition failure in production mode.

## 6. State and commit ownership

The architecture must explicitly choose whether authoritative operation state is owned by JARVIS state store, Core StateStore/SQLite StateJournal, RuntimeEngine StateJournal, or a distinct canonical Operation Ledger.

Do not make several local journals appear globally atomic through matching IDs or sequential writes. The selected owner must provide stable operation/attempt identity, reservation/fencing, durable effect/unknown-outcome records, typed verification and external commit receipts, append-only audit linkage, transactional outbox/inbox or a documented saga/reconciliation protocol, and deterministic crash recovery/duplicate suppression.

Other runtimes may maintain projections/caches, but only one logical authority decides canonical operation state. Financial ledgers remain separate domain authorities and consume verified operation receipts.

## 7. HYPERSYNTH and JARVIS separation

HYPERSYNTH is the cognitive planning authority: it generates alternatives, plans, simulations and recommendations. It must not mint execution grants or write final committed memory from its own output.

JARVIS is a user-facing interaction/orchestration surface, not a second competing execution authority. It may translate intent and present plans, but delegates execution through the declared Runtime/Action Gate and consumes typed receipts.

Agent Fabric selects qualified agents and gathers independent results; it cannot grant capabilities. ModelFabric selects model/provider adapters but cannot promote model output to verified fact. Provider resilience may retry only where idempotency or target reconciliation makes retry safe.

The runtime owns operation state and external effect reconciliation. Verification owns evidence admission. Memory persists only claims admitted under declared policy.

## 8. Required closure evidence

Before claiming system-wide composition closure, later integration/validation must demonstrate:
- route inventory and authenticated-principal tests for every ingress;
- CompositionManifest generated from actual dependency injection and compared to approved manifest;
- no unregistered RuntimeEngine/HypersynthRuntime/JarvisRuntime construction in production paths;
- explicit ownership graph with no duplicate authority or orphaned component;
- cross-store failure injection between reservation, dispatch, effect, verification and commit;
- provider timeout/unknown-effect/idempotency tests;
- recovery epoch and stale lease fencing across restart and node replacement;
- per-route egress enforcement and browser subresource coverage;
- signed operation/receipt conformance across Python/Kotlin/Go/Rust;
- readiness tests with missing or misbound dependencies;
- independent audit of reverse-proxy, device-owner, KMS/HSM and deployment controls.

The existing structural closure gate remains one layer, but must be reported as structural closure and combined with composition, runtime, security, evidence and external assurance gates.

## 9. New bounded closure gaps

- `GAP-W01-W02-ALL-INGRESS-IDENTITY-AND-POLICY-PARITY`: inspected `/api/chat` directly invokes HYPERSYNTH while `/v1/session` and `/v1/execute` use gateway sessions; equivalent route-level identity/policy enforcement is not established.
- `GAP-W02-W04-CANONICAL-RUNTIME-PLANE-OWNERSHIP`: OperationalNORYXRuntime/HypersynthRuntime and JARVIS RuntimeEngine/Bridge are distinct compositions; ownership and delegation between cognitive, agent and execution planes are not fully normative.
- `GAP-W02-W03-W09-SINGLE-AUTHORITATIVE-OPERATION-STATE`: JARVIS state, Core StateStore/SQLite journal and RuntimeEngine StateJournal are separate state owners; one authoritative operation ledger and cross-store reconciliation contract is not established.
- `GAP-W01-W02-W09-PRODUCTION-COMPOSITION-MANIFEST-AND-ATTESTATION`: no inspected production manifest proves every ingress binds approved runtime, principal, policy, verifier, egress, state and recovery dependencies.
- `GAP-W06-W09-STRUCTURAL-VS-OPERATIONAL-CLOSURE-EVIDENCE`: global closure/completeness gates check imports, symbols, paths, registry shape and browser isolation, not end-to-end route composition or effect/commit evidence.
- `GAP-W04-W05-W09-POLYGLOT-SERVICE-AUTHORITY-PARITY`: Go gateway and Rust runtime stubs do not yet implement the same authenticated session, operation, authorization and signed receipt protocol as Python.
- `GAP-W02-W05-W11-PROVIDER-AND-EXECUTION-PLANE-RECONCILIATION`: JARVIS provider gateway/resilience, ModelFabric and RuntimeEngine/ToolExecutor paths need explicit operation identity, retry and effect ownership.

## 10. Decision status

This is a source-grounded architecture proposal, not an accepted ADR or implementation. It does not prove external reverse proxies or deployment controls are absent. It identifies what the inspected repository composition roots do and do not establish. No tests were run. W01–W12 remain **PARTIAL**.
