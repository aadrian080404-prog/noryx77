# NORYX7 — Ingress, external effects, release evidence and cross-workstream closure reconciliation

**Date:** 2026-11-25  
**Status:** architecture-only source reconciliation; proposed contracts, not implemented  
**Scope:** W01–W12; deepen existing ADR-B56–B62 without creating duplicate decision IDs.

## 1. Purpose and evidence boundary

This pass connects three source families that are often reviewed separately but jointly determine whether a NORYX7 operation is safe and traceable:

1. external ingress and surface authentication;
2. execution effects, retries, durable receipts and uncertain outcomes;
3. release, deployment, audit and architecture-closure evidence.

The inspected anchors are recorded in the existing repository inventory and source reconciliation documents. This document does not claim an exhaustive dynamic call graph, deployment inventory, production readiness or absence of uninspected paths. Source presence is evidence of a component, not proof that every caller uses it correctly.

No runtime, tests, workflows, dependencies, configuration or deployment files are changed. No test campaign is launched by this document.

## 2. Cross-stream findings

### 2.1 Ingress is not one uniform trust boundary — W01/W02/W08/W09

The repository inventory records distinct HTTP execution paths:
- `/v1/session` creates a gateway session;
- `/v1/execute` validates a Bearer session token and uses the gateway runtime adapter;
- `/api/chat` constructs a task and invokes `OperationalNORYXRuntime.run_hypersynth` directly in the inspected route.

The inspected `/api/chat` handler does not itself invoke the gateway session validator. Whether an upstream proxy or deployment layer adds equivalent authentication is not established by the route source. Therefore the routes cannot be assumed equivalent, and this observation is not proof of an exploitable unauthenticated endpoint.

**Required architecture contract:** every ingress adapter must produce a normalized request envelope containing verified principal, tenant/scope, authentication assurance, policy epoch, request/execution correlation, idempotency scope, risk class, deadline, cancellation signal and provenance of the identity assertion. A route may delegate authentication to a trusted upstream only if that trust boundary, header stripping/rewriting rules and authenticated channel are explicitly specified.

The gateway and direct operational route must converge before privileged planning/dispatch on the same canonical authorization and audit contract. Health/readiness routes remain non-privileged and disclose minimum operational metadata.

### 2.2 External side effects and durable state are separate facts — W02/W03/W05/W08/W09/W11

The source reconciliation identifies provider routing, provider execution gateway and provider resilience as distinct layers. Provider routing may retry after exceptions; a separate resilience wrapper also tracks bounded attempts. A stable action identifier that is reused across a logical operation is not, by itself, proof that each attempt is uniquely attributable or that the downstream target enforces idempotency.

**Required architecture contract:** define a logical operation ID, attempt ID, target idempotency key, effect class, dispatch receipt, target acknowledgement, observation time, retry budget and compensation policy as distinct fields. The contract must state which layer owns retry, whether retries are safe for each effect class, and how duplicate/unknown target outcomes are reconciled.

Canonical outcome vocabulary must distinguish at least:
- `NOT_DISPATCHED`: no external dispatch was attempted;
- `DISPATCH_UNKNOWN`: dispatch may have reached the target;
- `TARGET_ACCEPTED`: target acknowledgement exists;
- `EFFECT_OBSERVED`: independently observed effect evidence exists;
- `RESULT_ADMITTED`: result passed its receiving contract;
- `STATE_COMMITTED`: authoritative durable state transition exists;
- `COMPENSATION_REQUIRED`, `COMPENSATION_PENDING`, `COMPENSATED`;
- `INDETERMINATE`: available evidence cannot establish whether the effect occurred.

A timeout or exception after dispatch must not be translated to “no effect”. A journal append rollback is not compensation for a real external action. Cross-journal or cross-service operations require explicit saga/correlation semantics, not a claim of one atomic transaction.

### 2.3 Retry ownership must be singular per boundary — W02/W04/W05/W11

ProviderRouter, ProviderExecutionGateway and ResilientProviderExecutor are separate source components. Their composed retry behavior must be calculated across layers; local attempt limits can multiply when nested. Agent retry, provider retry, scheduler requeue and runtime recovery are not interchangeable.

**Required architecture contract:** one retry coordinator per logical operation, with downstream components returning classified outcomes rather than independently multiplying attempts. Every retry must re-evaluate principal validity, delegation lease, provider trust, data residency, budget, deadline, cancellation and idempotency. Non-idempotent actions require target-supported idempotency or a reconciliation workflow before retry.

### 2.4 Scheduler order is not proof of parallel execution — W02/W04/W05/W11

The inspected scheduler is topological/dependency oriented. Broader architecture goals include multi-agent and distributed execution, but a dependency-safe ordering function alone does not establish bounded parallel dispatch, resource reservation or cancellation propagation.

**Required architecture contract:** separate plan ordering, concurrency admission, resource reservation and dispatch. For every parallel group declare dependency edges, maximum concurrency, resource envelope, failure policy, cancellation propagation, result join rule and partial-result semantics. An implementation may execute sequentially while the contract remains capable of bounded parallel execution; do not describe one as the other.

### 2.5 Structural closure, CI success and operational release are different evidence — W06/W09/W11

Repository audit/inventory scripts inspect configured roots and selected syntax/keywords. They cannot prove dynamic caller completeness, deployment configuration, external trust, semantic validity or domain safety. CI workflow success applies to a particular commit and workflow scope; it does not approve an architecture freeze or production release.

**Required evidence model:** every claim of completeness must carry subject, scope, repository revision, configuration, evidence producer, method, raw artifact/result reference, timestamp, limitations and independent reviewer where required. Separate:
- structural inventory result;
- source/call-path reconciliation;
- architecture decision acceptance;
- implementation traceability;
- automated test/CI result;
- deployment/release approval;
- runtime operational evidence.

No generic `PASS` or `COMPLETE` label may erase these distinctions.

## 3. Canonical cross-stream contracts

| Contract | Canonical owner (logical) | Required consumers | Must not be conflated with |
|---|---|---|---|
| Principal and ingress assertion | W01 authority chain | W02 runtime, W08 surfaces, W09 security | client ID, agent ID, device ID, session token |
| Request/execution lifecycle | W02 coordinator proposal | W04 fabric, W05 scheduler/provider, W08 adapters | cognitive plan, runtime process, action ID |
| Action envelope and dispatch receipt | W01 capability/action authority + W02 dispatch boundary | W05 adapters, W09 egress, W03 journal | model tool-call proposal, agent skill |
| Effect/idempotency protocol | W03 state contract + W05 effect coordinator proposal | W02 runtime, W08 offline, W09 recovery, W11 operations | retry counter, state commit, compensation |
| Agent delegation and result admission | W04 canonical fabric proposal | W01 authority, W03 state, W06 evidence | registry membership, health, consensus |
| Provider/model binding and placement lease | W05 routing separation | W02 runtime, W08 distribution, W11 capacity | action authorization, agent identity |
| Evidence and closure assertion | W06 provenance/assurance contract | W07 simulation, W09 audit, W10 domains, W11 CI/release, W12 impact | hash-only digest, caller pass flag, CI green |
| Domain validity and human escalation | W10 domain manifests | W01 consent/authority, W06 evidence, W09 security | specialist keyword route, skill label |
| Financial/community record | W12 segregated ledger governance | W10 outcomes, W11 metering, external audit | runtime state, capability authority, reputation |

These are logical responsibilities. They do not appoint a concrete source class as canonical until constructor, caller, persistence and enforcement evidence is complete.

## 4. ADR-B56–B62 reconciliation

| Existing decision | Cross-stream clarification | Required closure evidence |
|---|---|---|
| B56 — indeterminate effects and compensation | One shared outcome state machine across runtime, adapters, journals and offline queues | Per-adapter effect taxonomy, receipts, crash windows, compensation and reconciliation matrix |
| B57 — scheduler vs parallel execution | Ordering, concurrency admission, resource reservation and dispatch are separate contracts | Call graph, concurrency semantics, cancellation/join behavior, resource accounting |
| B58 — model attestation | Distinguish integrity digest, keyed authentication, signer identity and model/provider provenance | Key custody, signer binding, artifact/model version, caller verification and revocation |
| B59 — provider metering | Static metadata is not measured usage or billing truth | Provider receipts, normalized units, actual usage/cost/latency, stale-data policy, disputes |
| B60 — API route authentication | Gateway session and direct `/api/chat` path need explicit trust-boundary equivalence or deliberate separation | All route definitions, middleware/proxy config, principal source, auth tests as later phase, audit mapping |
| B61 — platform release coverage | Platform artifacts need explicit build/test/sign/promote/rollback evidence | Per-platform artifact matrix, iOS/Android/browser/backend coverage, release provenance |
| B62 — audit script semantics | Structural checks cannot claim architecture or operational closure | Machine-readable evidence schema, scan roots, exclusions, revision pinning, false-positive/negative limits |

No new ADR IDs are introduced. B56–B62 remain OPEN until their evidence is attached and reviewed.

## 5. W01–W12 simultaneous impact map

| Stream | New reconciliation obligation | Dependency / blocker |
|---|---|---|
| W01 Authority & identity | Normalize principal assertions at every ingress; bind tenant, session, workload and device scopes | Blocks privileged paths in W02/W04/W05/W08/W09 |
| W02 Runtime topology | Converge gateway/direct routes on one logical lifecycle and outcome protocol | Depends on W01; unresolved composition-root/facade ownership |
| W03 State & recovery | Persist operation/attempt/receipt/effect state with explicit journal namespace and saga boundaries | Depends on W01/W02; durable reservation and restore semantics open |
| W04 Agent fabric | Propagate request/delegation IDs, cancellation and result-admission state across all invocation paths | Depends on W01/W02; direct invocation inventory open |
| W05 Routing & resources | Compose provider/agent/scheduler/placement budgets and singular retry ownership | Depends on W01/W02/W04; enforcement and capacity reservation open |
| W06 Semantics & evidence | Define evidence objects for ingress assertions, target receipts, result admission and closure claims | Depends on W01/W03; source lineage and independent evaluation open |
| W07 MIRROR WORLD | Keep synthetic simulation outcomes distinct from observed real-world effects | Depends on W06 and W09; calibration and Reality Bridge open |
| W08 Surfaces & distribution | Ensure Browser/JARVIS/device/offline paths preserve the same identity, idempotency and outcome semantics | Depends on W01/W02/W05; offline trust and reconciliation open |
| W09 Security & assurance | Bind ingress, egress, signer/key lifecycle, receipts, audit and recovery into one trust chain | Depends on W01/W03; root custody and enforcement inventory open |
| W10 Domain fabrics | Require domain-specific validity, jurisdiction, consent and human escalation before real-world effects | Depends on W06/W09; specialist qualification open |
| W11 Performance & operations | Meter actual resource use, bound concurrency/retries, and separate CI from release/operations | Depends on W05/W08; deployment source of truth and fleet SLOs open |
| W12 Product & ecosystem | Keep provider billing, financial ledger, donations and community outcomes outside execution authority | Depends on W09/W10/W11; governance and independent impact verification open |

Discovery continues in parallel. Contract acceptance remains dependency-ordered: W01 identity/authority and W06 evidence semantics are prerequisites for several downstream freezes; this does not require pausing discovery in other streams.

## 6. Required source evidence package before any freeze

For each ingress, runtime, agent, provider, tool, device and external-effect path, the source ledger must eventually capture:

1. exact path and immutable repository revision;
2. constructor/composition root and registration site;
3. public entrypoint and every known caller;
4. principal source and authentication assurance;
5. policy/capability check and enforcement location;
6. request, execution, action, attempt and idempotency identifier derivation;
7. state stores, journals, namespaces and persistence durability;
8. outbound network/device/provider side effect;
9. receipt, attestation, result admission and audit record;
10. timeout, cancellation, retry, crash, replay, offline and recovery behavior;
11. configuration/deployment assumptions and external trust boundaries;
12. evidence limitations and unresolved callers.

A missing caller graph is an explicit unknown, not proof of safety or a proven vulnerability. A path that cannot be traced end-to-end remains unaccepted for architecture freeze.

## 7. Architecture closure gates

- **Gate A — Inventory:** all relevant packages, routes, adapters, stores and external effects enumerated with exclusions.
- **Gate B — Ownership:** every authority, lifecycle, state namespace, retry coordinator and ledger has one logical owner.
- **Gate C — Contract:** identifiers, schemas, state transitions, failure semantics, trust epochs and cross-domain handoffs are explicit.
- **Gate D — Evidence:** claims are traceable to source/revision and evidence method; independent evidence is actually independent.
- **Gate E — Reconciliation:** all collisions, open ADRs, deferred scopes and compatibility obligations have accepted dispositions.
- **Gate F — Freeze manifest:** accepted contract versions, residual risks, deferred items, source anchors and approval are recorded.

Passing a gate requires evidence for that gate. CI success, structural completeness, or document count cannot substitute for any gate.

## 8. Current disposition

- ADR-001 plane count remains the only accepted documentation decision in the current ADR set; it does not establish full architecture completion.
- ADR-002 through ADR-005 remain proposed pending their source/call-site acceptance evidence.
- ADR-B56–B62 remain OPEN.
- W01–W12 remain PARTIAL; no workstream is declared DECIDED or FROZEN by this document.
- The next cycle should collect route/middleware/deployment evidence, complete effect-adapter and retry call graphs, map per-platform release artifacts, and bind all results into the existing source ledger and gap register.
- No implementation, integration, manual test campaign, merge or deployment is authorized by this reconciliation.
