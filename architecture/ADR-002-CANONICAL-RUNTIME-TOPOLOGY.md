# ADR-002 — Canonical runtime topology and facade ownership

**Status:** Proposed architecture decision; source-inspected, not implemented  
**Date:** 2026-11-21  
**Scope:** runtime ownership, composition, compatibility and lifecycle

## Context and observed source

The repository contains several runtime-shaped components with overlapping responsibilities:

- `core/runtime.py` defines `NORYXRuntime`, composes policy, verification, recovery, security, ActionGate, memory, state, audit, identity, resource routing, decomposition and HYPERSYNTH.
- `core/hypersynth_runtime.py` defines `HypersynthRuntime`, independently composes several of the same safety dependencies and constructs the HYPERSYNTH kernel/tool executor.
- `core/operational_runtime.py` subclasses `NORYXRuntime`, starts hosted agents and installs `OperationalAgentFabric` as the HYPERSYNTH supervisor.
- `noryx7_runtime/engine.py` defines a separate operational data-plane engine with its own execution lifecycle, scheduler, adapter, attestation signer, identity registry, authorization provider, replay guard and optional state journal.
- `noryx7_runtime/state.py` defines an append-only signed `StateJournal`; this is not the same abstraction as `core/state.py` / `core/state_journal.py`.
- JARVIS has a surface/runtime role and must not become a second authority plane.

These are concrete source observations, not proof that all call paths or deployments have been inspected.

## Decision proposal

Adopt a **single logical runtime authority with bounded execution engines**, rather than forcing every existing class into one large class.

1. **System Runtime Coordinator (SRC)** — the sole lifecycle coordinator and composition root. Owns request/session lifecycle, canonical policy context, cancellation/deadline propagation, execution correlation, recovery epoch and final result state.
2. **Cognitive Runtime (CR)** — HYPERSYNTH cognition: understanding, decomposition, planning, hypothesis work, agent selection, synthesis and result proposal. It does not independently own durable commit authority.
3. **Action Runtime (AR)** — bounded execution of authorized action envelopes. Enforces capability and ActionGate decisions at the last responsible moment; produces attestations and execution outcomes.
4. **State Authority (SA)** — canonical journal/commit interface. Owns durable state transitions, idempotency reservation, append/commit ordering and recovery checkpoints.
5. **Surface Adapters** — JARVIS, Browser, API, terminal and device adapters. They normalize user input and display status; they never create authority or bypass SRC.
6. **Compatibility Facades** — existing `NORYXRuntime`, `HypersynthRuntime`, `OperationalNORYXRuntime` and `RuntimeEngine` remain adapters/facades during migration. Their current public contracts are preserved until explicit deprecation.

## Canonical call graph

```text
Surface / API / Device
        |
        v
System Runtime Coordinator
  | identity + session + policy context
  | deadlines + cancellation + recovery epoch
  |
  +--> Cognitive Runtime (HYPERSYNTH)
  |       | plan / hypotheses / agent proposals
  |       +--> Agent Fabric (bounded delegation)
  |
  +--> Capability Broker + ActionGate
          | signed/authorized ActionEnvelope
          v
      Action Runtime
          | adapter execution
          | attestation + result evidence
          v
      State Authority
          | reserve -> append -> verify -> commit
          v
      Coordinator finalizes outcome + audit reference
```

This is a logical ownership graph, not a claim that the current implementation already follows it.

## Ownership invariants

- Exactly one coordinator owns each top-level request lifecycle.
- Exactly one authority owns each durable state namespace and commit sequence.
- Cognitive planning can propose actions but cannot grant capabilities.
- Agent selection cannot bypass the ActionGate or action runtime.
- A surface cannot supply trusted principal identity by unverified request metadata.
- Action execution and durable commit are distinct states; an external side effect may have occurred even if commit is indeterminate.
- Recovery cannot silently replay a non-idempotent side effect.
- A runtime facade may delegate, but may not maintain a conflicting policy, identity, journal or recovery authority.
- Runtime IDs, execution IDs, principal IDs and action IDs have distinct meanings and explicit binding rules.

## Compatibility and migration proposal

- Phase A: inventory constructor dependencies and public call signatures for each facade; freeze current behavior as compatibility constraints.
- Phase B: define common coordinator, action-envelope, outcome and state-authority contracts in architecture only.
- Phase C: designate one existing runtime composition as the initial coordinator implementation candidate; retain others as facades.
- Phase D: migrate one call path at a time behind adapters; no dual-write state ownership.
- Phase E: remove duplicate ownership only after call-site and persisted-data migration evidence exists.

No source code changes are authorized by this ADR.

## Alternatives considered

- **One monolithic runtime class:** rejected; creates a high-coupling object and merges cognition with privileged execution.
- **Independent peer runtimes:** rejected as canonical topology; allows divergent policy, recovery and state semantics.
- **Immediate replacement of all current runtimes:** rejected; unsafe without a complete compatibility and persistence migration inventory.
- **Logical coordinator plus specialized engines:** proposed; preserves separation of concerns and supports gradual facade migration.

## Failure semantics

- Coordinator unavailable: reject new privileged work; do not fall back to an ungoverned runtime.
- Cognitive runtime unavailable: return unavailable/degraded; do not synthesize authorization.
- Action runtime unavailable: no dispatch; preserve a non-executed outcome.
- State authority unavailable before dispatch: block actions requiring durable reservation.
- State authority unavailable after external side effect: mark outcome indeterminate, quarantine reconciliation and never claim rollback unless the target confirms it.
- Conflicting runtime or journal identity: fail closed.

## Open questions

- Which existing runtime is the least disruptive first coordinator candidate?
- Are the two journal implementations intended for separate trust domains or are they competing state authorities?
- Which JARVIS operations are local presentation versus privileged action requests?
- What durable state is shared across core runtime and `noryx7_runtime`, if any?

## Acceptance evidence before architecture freeze

- Complete constructor/call-site inventory for all runtime entry points.
- One owner for request lifecycle, policy context, recovery epoch and final outcome.
- One owner per durable namespace, with explicit cross-namespace transaction semantics.
- Facade-to-canonical-contract compatibility matrix.
- Failure and cancellation state-transition tables.
- No unresolved path that can dispatch privileged work outside the canonical coordinator/action boundary.


## Additional source reconciliation — composition-root conflict (2026-11-22)

A deeper source pass identified additional runtime/execution authorities:
- `core/system_fabric.py` defines `CanonicalSystemFabric`, described as a shared execution substrate for JARVIS and NORYX7 and binds RuntimeEngine, ToolExecutor, VerificationEngine, AuthorizationAuthority, principal and policy by object identity.
- `core/execution_fabric.py` defines a separate environment adapter registry with its own mandatory authorization callback.
- `noryx7_runtime/engine.py` defines RuntimeEngine as a data-plane kernel with scheduler, adapter, signer, identity registry, optional state journal, multi-authorization authority, authorization provider and replay guard.
- `core/control_plane.py` composes recovery and defense state machines and artifact admission.

These sources introduce a material topology ambiguity. ADR-002's proposed System Runtime Coordinator, CanonicalSystemFabric, RuntimeEngine and ExecutionFabric may form composable layers, but the actual hierarchy is not established by class names. **ADR-002 remains open and must not be frozen** until the full constructor/call-site graph identifies one request-lifecycle owner, one privileged dispatch boundary and all compatibility facades.

New source review: `NORYX7_DEEP_SOURCE_RECONCILIATION_ALL_WORKSTREAMS.md`. This is bounded inspection, not exhaustive caller inventory.


## Polyglot composition and JARVIS source reconciliation — 2026-11-22

The repository's JARVIS runtime is not a peer action engine by default: `jarvis/core/runtime.py` composes `RuntimeEngine`, `CanonicalSystemFabric`, `JarvisRuntimeBridge`, core `ActionGate`/`ToolExecutor`, a JARVIS Policy, JARVIS request state and a separate JARVIS audit log. The bridge explicitly maps JARVIS plans to RuntimeEngine steps. JARVIS user-level grants and core cryptographic agent authorization are layered checks and must be documented as separate scopes.

The Go service currently exposes health and SHA-256 digest endpoints; the Rust library currently exposes an execution-envelope digest and deny-by-default helper. They are not equivalent to the Python runtime. The iOS actor has local expiring grants and a bounded consumed-action set; the Android audio bridge is an interface contract; the Android Browser uses HTTPS outside debug and authenticates to the Python gateway using bootstrap/session tokens. `render.yaml` describes one Python web service, not every artifact in the repository.

The exact JARVIS composition path is evidence against treating ADR-002's SRC diagram as already implemented. ADR-002 remains proposed pending complete call-site and lifecycle mapping.
