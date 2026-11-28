# NORYX7 — Repository Source Inventory and Execution-Path Reconciliation

**Status:** bounded repository inventory and source reconciliation; architecture only  
**Date:** 2026-11-22  
**Source snapshot:** `main`, previously identified as `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Scope:** no code changes, tests, dependencies, integration, merge or deployment

## 1. Repository inventory baseline

The recursive Git tree inspected for `main` returned **507 entries: 426 blobs and 81 tree/directory entries**. This is a reproducible inventory snapshot, not proof that every file's semantics or call sites have been read.

| Top-level area | Blob count | Primary architecture relevance |
|---|---:|---|
| `.github` | 8 | CI workflows and repository ownership |
| root | 13 | bootstrap, operational entrypoints, requirements, Render config, source dump |
| `architecture` | 19 | existing architecture documents and design references |
| `core` | 150 | cognitive, security, runtime, agent, memory, routing and tests |
| `devtools` | 25 | architecture audit, integration/repair scripts and local test lab |
| `docs` | 2 | source protection and Browser isolation notes |
| `ecosystem` | 15 | four-front boundaries, global fabric, scale and dispatch |
| `gateway` | 5 | HTTP session/auth/runtime adapter |
| `ios` | 4 | iOS platform adapter and tests |
| `jarvis` | 37 | JARVIS front, runtime, memory, policy, providers and tests |
| `noryx-browser` | 30 | Android Browser application, Gradle, navigation and gateway client |
| `noryx7_runtime` | 29 | execution engine, lifecycle, scheduler, adapters, model fabric, journal and tests |
| `services` | 4 | Go gateway and Rust runtime artifacts |
| `tests` | 69 | cross-system, gateway, offline, recovery, scale and architecture tests |
| other areas | 11 | Android bridge, reports, tools, UI and web entrypoints |

The seven workflow files are:
- `.github/workflows/core-verification.yml`
- `.github/workflows/jarvis-polyglot-verification.yml`
- `.github/workflows/million-scale-verification.yml`
- `.github/workflows/noryx7-foundation.yml`
- `.github/workflows/runner-smoke.yml`
- `.github/workflows/source-secrecy.yml`
- `.github/workflows/tests.yml`

The source tree includes iOS package tests, Android Browser Gradle tests, Go/Rust service tests, Python runtime tests and cross-system pytest suites. The inspected workflow inventory explicitly includes Python, Go and Rust in the JARVIS polyglot workflow and Browser Gradle tests in the foundation workflow. A dedicated iOS build/test workflow was not found among the seven workflow files; this is a CI coverage gap to decide, not a claim that iOS code is defective.

## 2. RuntimeEngine execution semantics — source reconciliation

### 2.1 Observed lifecycle

`noryx7_runtime/contracts.py` defines:
`CREATED, RUNNING, SUCCEEDED, REJECTED, FAILED, CANCELLED`.

`noryx7_runtime/lifecycle.py` enforces terminal transitions. The current enum does not separately represent `INDETERMINATE`, `PARTIAL`, `COMPENSATION_PENDING` or `QUARANTINED`. The architecture must define these outcomes before cross-front retry and side-effect reconciliation are frozen.

### 2.2 Scheduler semantics

`noryx7_runtime/scheduler.py` validates unique step IDs, dependency references and cycles, then produces a deterministic topological ordering. It groups currently ready steps in sorted order, but `RuntimeEngine.execute` iterates the resulting order sequentially.

Therefore the observed scheduler is a dependency-ordering scheduler, not evidence of concurrent execution. Parallel scheduling requires a separate bounded executor contract for concurrency, capacity, cancellation, failure propagation, result ordering and fairness.

### 2.3 Dispatch reservation and uncertain outcomes

Observed RuntimeEngine sequence:
1. Construct action envelope with execution/principal/step identity and nonce.
2. Compute action digest and stable authorization statement.
3. Apply high-risk multi-authorization and replay protection where configured.
4. Reserve the step in the optional state journal before dispatch.
5. Dispatch through adapter or supplied executor.
6. Verify output and create signed attestation when configured.
7. Append attestation and invoke optional committer.
8. Restore the pre-dispatch reservation if post-append commit fails, to keep the step blocked from duplicate dispatch.

The reservation is an important replay barrier. However, the returned lifecycle can still be `FAILED` after the external effect may have happened. The architecture should represent this as an indeterminate/commit-reconciliation outcome rather than imply that the external action definitely failed. The exact recovery process must query the target or reconcile by idempotency key before retry.

### 2.4 Runtime execution contract still open

- Durable reservation backend and atomicity under process crash.
- State-journal ownership and namespace.
- External target idempotency contract.
- Committer transaction boundary and outbox/inbox.
- Result/attestation append order and recovery after partial persistence.
- Timeout after dispatch and cancellation semantics.
- Compensation policy for reversible vs irreversible actions.
- Cross-runtime recovery epoch and authorization revocation synchronization.

## 3. Model Fabric and external model provider

### 3.1 Observed ModelFabric contract

`noryx7_runtime/model_fabric.py` defines:
- capability-based candidate selection;
- max cost and expected latency filters;
- minimum/maximum model fan-out;
- deterministic candidate ranking;
- canonical request and output digests;
- optional runtime identity binding;
- optional HMAC result binding when a binding key is supplied;
- optional verifier and synthesizer callbacks;
- degraded status when fewer than selected models return.

### 3.2 Integrity boundary

When a binding key is configured, the result MAC is HMAC-SHA256 over runtime identity, request digest, output digest and selected model. Without a binding key, the field named `result_mac` is a deterministic digest, not a keyed MAC or proof of origin. Architecture and telemetry must distinguish **integrity digest** from **authenticated result attestation**.

ModelFabric's runtime identity binding is also optional at construction. Production trust requirements must decide when it is mandatory and how its key is provisioned, rotated and revoked.

### 3.3 OpenRouter adapter observations

`noryx7_runtime/model_adapters/openrouter.py`:
- sends a non-streaming text chat-completion request;
- rejects non-empty tools because the current adapter contract is string-only;
- uses a configured model and API key;
- has a bounded request timeout;
- exposes a static `cost_per_call=0.0` and `expected_latency_ms=5000.0` metadata value.

Those values are adapter metadata, not measured current price or latency. Model routing must eventually use provider-reported or metered usage and observed latency/cost, with stale-estimate and quota semantics. Tool execution remains separate from model generation and must be authorized by the canonical tool/action path.

### 3.4 Model routing contract

A model candidate is eligible only if its capability, data policy, region, privacy, risk, cost ceiling, latency ceiling, provider status and schema compatibility satisfy the request. Candidate selection does not grant the model permission to execute tools. A model-generated tool proposal is a request to the action broker, not a capability.

## 4. HTTP surface and gateway path reconciliation

### 4.1 Observed web entrypoints

`web/app.py` defines:
- `/health` and `/v1/health`;
- `/v1/session` to create a gateway session;
- `/v1/execute` using a Bearer session token and the gateway runtime adapter;
- a separate `/api/chat` route that constructs a TaskSpec and invokes `OperationalNORYXRuntime.run_hypersynth` directly.

The `/api/chat` handler does not itself call the gateway session validator in the inspected route. Whether an upstream deployment layer adds authentication is not established by this source. The two request paths therefore require an explicit route-level security and lifecycle decision; they must not be assumed equivalent.

### 4.2 Canonical API boundary

Every externally reachable route must declare:
- authentication mechanism and verified principal source;
- tenant/scope and request size limits;
- authorization policy and risk classification;
- execution/task/idempotency/correlation identifiers;
- rate and cost limits;
- data residency and provider routing constraints;
- result/partial/indeterminate semantics;
- audit event and privacy-safe logging policy.

Health endpoints disclose only the minimum operational metadata needed for monitoring. They do not expose credentials, prompt contents, memory or sensitive agent state.

## 5. Developer tools and structural-audit boundaries

### 5.1 Test Lab

`devtools/test_lab/runner.py` declares a fixed allowlist of compile, pytest, closure and completeness commands; it is described as local-only and is not imported by production runtime. Its existence is a development control, not proof that tests have run or passed in the current branch.

### 5.2 Architecture inventory scripts

`devtools/audit_next_architecture_phase.py` scans selected Python roots and uses AST parsing to list modules, imports, classes and functions. `devtools/consolidate_architecture_phase.py` resolves expected capabilities using expected paths and selected class/function keywords.

These tools are useful inventory aids, but they do not establish:
- dynamic call graphs or callback invocation;
- constructor dependency injection at runtime;
- external deployment and configuration;
- authority equivalence or transaction semantics;
- semantic correctness or domain validity;
- complete repository coverage outside their configured scan roots.

An audit script printing COMPLETE or PASS must be interpreted according to its exact checks and source revision, not as a global architecture-complete assertion.

### 5.3 CI as a separate evidence stream

Pull-request workflows may run automatically after documentation commits. This architecture phase does not manually launch or expand test campaigns. Automatic workflow results, when complete, are reported separately from architecture status and do not authorize integration or freeze.

## 6. Additional open decisions

| ID | Priority | Decision | Affected streams | Required output |
|---|---|---|---|---|
| ADR-B56 | B0 | RuntimeEngine lifecycle states for indeterminate side effects, partial results and compensation | W02, W03, W08, W09, W11 | Canonical outcome/state-transition matrix |
| ADR-B57 | B0 | Topological ordering vs actual parallel execution and bounded scheduler ownership | W02, W04, W05, W11 | Concurrency, dependency and cancellation contract |
| ADR-B58 | B1 | ModelFabric keyed attestation requirements and mandatory runtime binding | W01, W05, W06, W09 | Model result trust profile and key lifecycle |
| ADR-B59 | B1 | Provider usage/cost/latency metering and stale metadata handling | W05, W11, W12 | Metering contract and provider reconciliation |
| ADR-B60 | B0 | Route-level API authentication and equivalence between /api/chat and /v1 gateway routes | W01, W02, W08, W09 | Endpoint inventory, principal source and authorization matrix |
| ADR-B61 | B1 | CI coverage for iOS adapter and explicit per-artifact release evidence | W08, W11 | Platform verification/release coverage matrix |
| ADR-B62 | B1 | Architecture audit scripts: scope, completeness claims and machine-readable evidence schema | W02, W06, W11 | Audit evidence contract and limitations |

These decisions remain open. They do not authorize implementation or tests.

## 7. Updated gap classifications

- **AMBIGUOUS:** separate direct `/api/chat` and gateway session execution paths.
- **UNSUPPORTED / UNVERIFIED:** iOS CI workflow not found in the inspected workflow inventory.
- **UNBOUNDED / HIDDEN-COUPLING:** external side effect followed by commit failure, despite reservation retention.
- **AMBIGUOUS:** sequential topological scheduler described alongside broader parallel-agent goals.
- **UNVERIFIED:** unkeyed ModelFabric result digest can be misinterpreted as authenticated MAC.
- **STALE / UNVERIFIED:** static provider cost and latency metadata.
- **UNSUPPORTED:** current OpenRouter adapter does not expose tool calling through its ModelAdapter contract.
- **GOVERNANCE-GAP:** audit script output labels lack a common evidence scope/acceptance schema.

## 8. Explicit scope boundary

No source implementation, workflow, test, dependency, configuration, deployment or runtime behavior was changed by this document. No tests or benchmarks were executed manually. The full architecture remains PARTIAL pending source/call-graph completion and ADR resolution.
