# NORYX7 — Deep source reconciliation and topology conflicts (all workstreams)

**Inspected source ref:** `main` at `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Architecture branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Status:** active, bounded source reconciliation; not a completeness claim  
**Scope:** additional source families discovered after the first W01–W12 pass

## 1. Why this pass exists

The first source review identified the principal overlaps, but the repository contains additional execution, trust, offline, recovery and fabric abstractions that materially affect those decisions. This pass records those sources explicitly. It does not assume that similarly named components are interchangeable, and it does not infer production deployment from a class or test file.

The inspected set includes:
- `core/agent_identity.py`, `agent_mesh.py`, `agent_runtime.py`, `coordination.py`;
- `core/control_plane.py`, `execution_fabric.py`, `recovery.py`, `device.py`, `egress.py`, `system_fabric.py`, `architecture_registry.py`;
- `core/offline_adapters.py`, `offline_anchor.py`;
- `noryx7_runtime/engine.py`, `lifecycle.py`, `state.py`, `recovery.py`, `scheduler.py`, plus runtime contracts/adapters/attestation;
- repository inventories for `core/`, `noryx7_runtime/`, `jarvis/`, `ecosystem/`, `tests/` and `.github/workflows/`.

## 2. W01 — Identity, principal and capability authority

### Additional source observations

- `core/agent_identity.py` defines `AgentMission` and a mission lookup by agent ID. It is a role/mission descriptor, not cryptographic identity.
- `core/device.py` defines `DeviceIdentity`, trust states UNKNOWN/VERIFIED/REVOKED/ISOLATED, CLIENT/EDGE/CLOUD roles, capability grants and a `DeviceRuntimeBoundary`. Grants are checked against time and epoch.
- `core/agent_runtime.py` tracks agent lifecycle/status and heartbeat through a router and identity registry.
- `core/agent_mesh.py` defines role-based nodes/tasks and in-memory registration/routing.
- `core/identity.py` and `core/multiauth.py` remain distinct trust sources; device capability grants, mission descriptors and role-based routing must not be mistaken for principal authorization.

### Architecture consequences

1. Identity needs an explicit principal taxonomy: human, service, agent, device, workload, tenant, provider and external actor.
2. Every binding must identify issuer, subject, scope, audience, expiry, epoch, revocation source and proof type.
3. Mission/role/skill/capability are attributes, not identity credentials and not authorization by themselves.
4. Device capability authorization must be joined to current device trust, attestation, owner/principal delegation and the canonical policy epoch.
5. Agent heartbeat is liveness evidence only; it is not proof of trusted code, current authorization or safe operation.

### Open work

- Inventory every identity registry and device/agent binding store, including adapters and JARVIS-local identity.
- Define one trust-root lifecycle and explicit federation trust between nodes/tenants.
- Define stale heartbeat, device isolation, capability expiry and revocation propagation semantics.
- Distinguish a mission profile from an executable capability manifest and a signed authorization grant.

## 3. W02 — Runtime, composition root and execution fabrics

### Additional source observations

- `core/system_fabric.py` defines `CanonicalSystemFabric` as a shared execution substrate for JARVIS and NORYX7, binding a `RuntimeEngine`, `ToolExecutor`, `VerificationEngine`, `AuthorizationAuthority`, principal and policy by object identity.
- `core/execution_fabric.py` defines a separate environment adapter registry with observe/execute methods and an authorization callback checked immediately before execution.
- `noryx7_runtime/engine.py` defines `RuntimeEngine` as an operational data-plane kernel. It has its own scheduler, adapter, attestation signer, identity registry, runtime ID, optional journal, signed multi-authorization authority, authorization provider, high-risk action types and replay guard.
- `core/control_plane.py` composes a `RecoveryController`, defense controller, supply-chain verifier and event bus; it enforces synchronized recovery/defense states and controls artifact admission and recovery transitions.
- `core/runtime.py`, `core/hypersynth_runtime.py`, `core/operational_runtime.py`, `core/system_fabric.py`, `core/execution_fabric.py` and `noryx7_runtime/engine.py` therefore represent multiple runtime/composition/execution abstractions.

### Critical topology conflict

ADR-002 proposes one logical System Runtime Coordinator. `CanonicalSystemFabric` describes a shared execution substrate and asserts object-level consistency. `ExecutionFabric` separately owns environment adapters and its own authorization callback. `RuntimeEngine` owns an action execution lifecycle and optional state journal. These may be composable layers, but the source names alone do not establish the actual hierarchy or a single entrypoint.

**Do not freeze ADR-002 until this graph is resolved.** The canonical architecture must decide whether:
- SystemFabric is the composition root and RuntimeEngine is its execution kernel;
- SRC is an outer lifecycle coordinator and SystemFabric a shared dependency container;
- ExecutionFabric is the physical/tool adapter layer beneath RuntimeEngine;
- or one or more are compatibility/test facades.

The answer must come from constructor and call-site inventory, not naming.

### Required runtime contract

For each entrypoint record: process/service owner, surface, coordinator, principal establishment, policy epoch, recovery epoch, cognitive runtime, agent broker, action engine, execution fabric, tool executor, state namespace, verifier, audit sink, cancellation/deadline propagation and shutdown owner.

No surface may create a second authority by constructing its own policy, principal, journal or verifier objects without an explicit trust-domain boundary.

## 4. W03 — Journal, idempotency and recovery

### Additional source observations

- `noryx7_runtime/state.py` defines an append-only in-memory `StateJournal` with signed attestation verification, identity binding, runtime ID, step reservations, action digest, previous attestation digest and provenance seal. It aliases `StateStore = StateJournal` at the end of the module.
- `noryx7_runtime/engine.py` can reserve a step before dispatch and can append attestation-backed results through the journal.
- `noryx7_runtime/recovery.py` validates journal entries, attestations, identity and runtime identity.
- `core/state_journal.py` is a separate SQLite WAL journal with durable sequence/digest validation; `core/state.py` adds a different store/commit boundary.
- `core/recovery.py` defines a recovery state machine NORMAL, INCIDENT, LOCKDOWN, TRUSTED_ONLY, RECOVERY and VERIFIED, with an epoch and guarded transitions.
- `core/control_plane.py` coordinates its recovery controller with a defense controller and rejects desynchronization.
- `core/offline_anchor.py` persists a monotonic snapshot marker in SQLite WAL with synchronous FULL; its own documentation says production should protect storage or replace it with a hardware-backed TPM/HSM counter.

### Architecture consequences

1. There are at least two distinct journal implementations with materially different persistence properties: a runtime-level in-memory signed journal and a core SQLite digest journal. Their shared interface and intended domains are not yet proven.
2. A step reservation in an in-memory journal does not provide crash durability. Durable idempotency must be explicitly bound to the journal/namespace used by the dispatching engine.
3. Recovery state, defense mode, authorization epoch, snapshot monotonic marker and journal sequence are separate values. Their synchronization and restore ordering must be specified.
4. A locally persisted monotonic marker is not automatically tamper-proof if the storage itself can be rolled back or replaced.
5. A rollback operation on a journal append must not be interpreted as compensation of an external side effect.

### Required recovery matrix

Cover at least: process restart; host loss; partial write; corrupted/tampered journal; stale snapshot; lost signing key; revoked signer; clock rollback; offline partition; duplicate message; dispatch accepted but acknowledgement lost; target executed but local commit failed; schema migration with pending actions; backup restore to older epoch; and multi-region split brain.

For each case specify permitted read-only behavior, privileged-action behavior, operator approval, reconciliation source and whether the outcome is NOT_STARTED, RESERVED, DISPATCHED, ATTESTED, ADMITTED, COMMITTED, REJECTED, INDETERMINATE or COMPENSATION_PENDING.

## 5. W04 — Agent mesh, coordinator and delegation

### Additional source observations

- `core/agent_mesh.py` provides role-based in-memory registration and route selection.
- `core/agent_runtime.py` tracks startup, heartbeat, stop and online status.
- `core/coordination.py` defines `AgentCoordinator`, assignment, trusted-agent selection, execution and consensus verification.
- `core/agent_fabric.py` has a direct agent-run dispatch path.
- `core/operational_fabric.py` composes supervisor/resource routing/result admission.

### Architecture consequences

These are not one abstraction: mesh discovery, runtime liveness, task coordination, capability-based delegation, execution and result admission are separate lifecycle stages. The canonical agent fabric must state which are registries, selectors, supervisors, executors and evidence validators.

A consensus result is not independent merely because two agent IDs are different. Independence needs separate model/provider lineage, data sources, credentials or control domains where the use case requires it.

### Open work

- Trace every call to `AgentCore.run`, agent `execute`, collaboration helpers and JARVIS agent/tool execution.
- Map role, mission, skill, capability, lease, principal, selected-agent identity and signed action scope.
- Define agent enrollment, upgrade, quarantine, heartbeat expiry, cancellation, drain and decommission.
- Define whether consensus is voting, independent verification, evidence aggregation or merely multi-agent synthesis.

## 6. W05 — Action execution, tools, egress and resource placement

### Additional source observations

- `core/execution_fabric.py` registers environment adapters and requires an authorization callback before execution.
- `core/egress.py` defines a bounded explicit allowlist for component/host/port/protocol; the rules are held in memory.
- `core/device.py` gates device capabilities against time and epoch.
- `core/resource_router.py` selects device/edge/cloud tiers; `core/provider_router.py` selects providers; `core/router.py` selects agents.
- `noryx7_runtime/scheduler.py` orders plan steps; it is separate from provider and placement routing.

### Architecture consequences

The architecture needs distinct authorities for:
- tool/action authorization;
- environment adapter selection;
- network egress permission;
- provider/model selection;
- agent assignment;
- plan dependency scheduling;
- device/edge/cloud placement;
- capacity reservation and accounting.

An egress allowlist in memory does not establish network-level enforcement. It must be bound to the actual network boundary, DNS/IP resolution behavior, redirects, proxy path, IPv4/IPv6, TLS identity and policy update/revocation.

Resource placement must distinguish hard constraints (privacy, residency, safety, hardware capability, trust, authorization) from soft preferences (latency, cost, energy, performance).

## 7. W06 — Canonical architecture registry and verification semantics

### Additional source observations

- `core/architecture_registry.py` declares `CANONICAL_DEFINITIONS` for the architecture planes and a `canonical_gate()` / `require_structural_completeness()` helper.
- The registry records contract, implementation anchor, integration, trust, failure, budget, observability, recovery, verification and regression fields.
- `core/system_fabric.py` checks object identity across shared dependencies; this is an in-process composition invariant, not proof of distributed consistency or semantic correctness.

### Architecture consequences

The registry's structural completeness check and the proposed system-wide architecture freeze gate are different things. A plane can have a populated registry card while its implementation/callers/operational deployment remain only partially reconciled.

Add explicit per-capability status and source evidence; structural presence must never imply operational readiness.

## 8. W07 — MIRROR WORLD and Reality Bridge

The inspected `ExecutionFabric` is a generic environment adapter execution substrate with an authorization callback. It does not by itself define the full MIRROR WORLD Reality Bridge, world fidelity or physical safety model.

Keep separate:
- synthetic scenario execution;
- cyber-range execution;
- software/system emulation;
- calibrated engineering digital twin;
- scientific/environmental simulation;
- socio-economic/agent-based model;
- observation of a real environment;
- actuation in a real environment.

Each requires a distinct world manifest, fidelity/uncertainty model, allowed actions, data boundary, authorization scope, operator and evidence class. Real-world actuation requires physical interlocks and an independent emergency stop, not merely a software policy callback.

## 9. W08 — Offline, device and distributed trust

### Additional source observations

- `core/offline_adapters.py` adapts central policy, verification and authenticated encryption into offline contracts.
- `core/offline_anchor.py` uses a local SQLite monotonic marker; production hardware-backed anchoring remains an explicit deployment requirement.
- `core/device.py` provides local device identity and capability checks.
- `core/egress.py` holds local in-memory egress rules.
- `core/distributed.py` and `core/device_fabric.py` provide topology/device metadata and registries; metadata is not equivalent to authenticated distributed membership.

### Open work

Map concrete adapter composition, persistent outbox/inbox, signed snapshot issuer, trusted clock/monotonic source, anti-rollback root, policy epoch, revocation freshness, queue replay, conflict resolution, duplicate action suppression and device-loss recovery. Establish how offline action capabilities are constrained and whether the outbox can ever carry a previously authorized but now revoked action.

## 10. W09 — Security control plane and egress assurance

The control plane has a coordinated recovery/defense state machine and artifact admission. The egress policy provides a separate network allowlist. Secure boot and supply-chain verification are separate source families. Their relationship needs an explicit trust chain:

source provenance -> build provenance -> signed release manifest -> secure boot measurement -> runtime admission -> adapter/egress policy -> action authorization -> attestation -> journal/audit -> incident response.

Every link needs an issuer, verifier, freshness rule, revocation mechanism and recovery owner. Security telemetry is evidence about events, not the authority that determines the security state; the control-plane code itself documents this separation.

## 11. W10 — Domain packages and physical safety

The architecture registry and Universal Intelligence domain routing do not prove domain completeness. Domain contracts must also include physical constraints where a domain can control devices or infrastructure.

Each specialist package must declare:
- domain owner and expert escalation;
- jurisdiction/standard and version;
- ontology, units and coordinate systems;
- admissible evidence and uncertainty;
- model/tool validation envelope;
- prohibited operations and unsupported conditions;
- human review/consent threshold;
- data residency, retention and audit;
- physical safety limits, interlocks and emergency stop if actuators are in scope.

## 12. W11 — Operations and deployment

The repository inventory confirms seven GitHub Actions workflow definitions: core verification, JARVIS polyglot verification, million-scale verification, foundation, runner smoke, source secrecy and tests. These are CI workflows, not a complete deployment/operations architecture.

No `deployment/` or `infra/` directory was found at the inspected repository root. This is only a root-level directory observation; deployment may be defined through platform configuration or external service settings. The architecture still needs explicit runtime environments, artifact promotion, secrets/key injection, health/readiness, autoscaling, backup, disaster recovery, incident roles and release rollback.

## 13. W12 — Product/ecosystem governance

The ecosystem package includes structural closure/completeness, runtime dispatch, global memory and identity authorization indexes. These are not substitutes for product governance.

The architecture must keep separate:
- identity/authorization authority;
- tenant and organization directory;
- marketplace/provider trust;
- billing and payment processor;
- internal financial ledger;
- project/community contribution ledger;
- grants/donations and public-interest funds;
- dispute, refund, fraud and safeguarding process.

No marketplace listing, payment state, reputation score or community vote may grant system execution authority.

## 14. Newly identified architecture decisions

| ID | Priority | Decision | Required closure evidence |
|---|---|---|---|
| ADR-B22 | B0 | Relationship between CanonicalSystemFabric, SRC, RuntimeEngine and ExecutionFabric | Complete composition-root and constructor/call-site graph; one lifecycle owner; no shadow dispatch path |
| ADR-B23 | B0 | Canonical recovery/defense/authorization epoch coordination | Transition matrix, epoch owner, crash consistency and rollback-resistant persistence |
| ADR-B24 | B0 | Durable idempotency reservation and dispatch boundary | Reservation backend, atomicity, retention, cross-process semantics and uncertain-side-effect handling |
| ADR-B25 | B1 | AgentMesh/AgentRuntime/AgentCoordinator/AgentFabric responsibilities | Full call graph, role/skill/capability distinction, lease and independent consensus evidence |
| ADR-B26 | B1 | Actual enforcement boundary for egress and execution adapters | Network enforcement point, DNS/redirect behavior, policy distribution and revocation |
| ADR-B27 | B1 | Production monotonic anchor and offline trust root | Hardware/storage trust model, issuer, anti-rollback, recovery and freshness policy |
| ADR-B28 | B1 | Architecture registry completeness versus system freeze acceptance | Traceability schema and evidence-backed gate that cannot equate structural card presence with operational readiness |
| ADR-B29 | B1 | Deployment/operations source of truth | Explicit deployment inventory, runtime environments, secrets, release promotion, backup and DR |

These decisions are open, not defects proven and not implementation tasks.

## 15. Workstream status after this pass

| Workstream | New source anchors | Architecture status |
|---|---|---|
| W01 | agent_identity, device identity/capability gate, agent runtime | Partial; principal taxonomy and trust-root lifecycle open |
| W02 | CanonicalSystemFabric, ExecutionFabric, RuntimeEngine, ControlPlane | Partial; major composition-root ambiguity identified |
| W03 | runtime StateJournal, core SQLite StateJournal, RecoveryController, MonotonicAnchor | Partial; durability and epoch/recovery ordering open |
| W04 | AgentMesh, AgentRuntime, AgentCoordinator, AgentFabric, OperationalAgentFabric | Partial; dispatch/consensus graph open |
| W05 | ExecutionFabric, egress allowlist, device capability, provider/agent/resource routers, scheduler | Partial; actual enforcement and composed budgets open |
| W06 | architecture_registry and system_fabric consistency gate | Partial; structural completeness distinct from architecture freeze |
| W07 | ExecutionFabric adapter boundary | Partial; world fidelity and Reality Bridge still separate contracts |
| W08 | offline adapters/anchor, device trust, distributed metadata | Partial; hardware trust and sync semantics open |
| W09 | control plane, defense/recovery, egress, secure boot and supply chain | Partial; end-to-end chain and root custody open |
| W10 | plane registry and domain routing | Partial; specialist/physical safety manifests open |
| W11 | workflow inventory and local operations components | Partial; deployment source of truth and SLO/DR open |
| W12 | ecosystem runtime/structural fabrics | Partial; financial and community governance boundaries open |

## 16. Next discovery pass

Continue with full source inventories rather than only representative files:
1. Enumerate all Python packages and nested modules; identify duplicate symbols, imports and compatibility exports.
2. Trace constructors and call sites for all runtime, identity, journal, fabric, policy, tool and provider objects.
3. Inspect the entire JARVIS package and all browser/mobile/desktop surface source locations.
4. Inspect every offline adapter and test fixture to distinguish real implementation from protocol/stub.
5. Map configuration, secrets, deployment platform, CI/CD artifact chain and external runtime environment.
6. Map every persistent store, schema, migration, backup, restore and deletion path.
7. Map all external side-effect adapters and their idempotency/compensation contracts.
8. Map domain and product/ecosystem requirements to explicit owners and assurance criteria.

This pass is intentionally bounded. No source code, dependency, test, runtime integration, merge or deployment was changed.
