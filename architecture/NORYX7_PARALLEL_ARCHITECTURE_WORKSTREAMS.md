# NORYX7 — Parallel architecture workstreams and closure protocol

**Status:** active architecture-only coordination document  
**Date:** 2026-11-21  
**Parent:** System-Wide Architecture Closure Blueprint

## Objective

Close architecture faster by working in parallel on bounded workstreams while sharing one contract registry, one decision log and one freeze gate. “Parallel” means concurrent design/reconciliation, not parallel changes to runtime code.

## Workstream matrix

| Stream | Scope | Primary outputs | Dependencies | Closure evidence |
|---|---|---|---|---|
| W01 Authority & identity | Principal, session, policy, capability, ActionGate, revocation | Authority matrix, identity lifecycle, delegation rules | None; blocking | One authority chain and revocation contract |
| W02 Runtime topology | Core/HYPERSYNTH/operational/runtime engine/JARVIS | ADR-002, runtime graph, facade map | W01 | One coordinator and bounded engines |
| W03 State & recovery | StateStore, journals, attestation, checkpoints, offline restore | ADR-003, namespace matrix, recovery matrix | W01, W02 | One logical state authority |
| W04 Agent fabric | Native/operational fabric, supervisor, collaboration, hosted agents | ADR-004, lifecycle and delegation contract | W01, W02 | One dispatch/admission contract |
| W05 Routing & resources | Provider/model, agent, scheduler, placement, budgets | ADR-005, decision ownership matrix | W01, W02, W04 | Separate owners and hard constraints |
| W06 Semantics & evidence | NEXUS IR/Wire/Surface, ontology, evidence, FRL | Semantic schema and provenance ADRs | W01, W03 | Versioned schemas and evidence states |
| W07 MIRROR WORLD | World graph, scenarios, simulation, cyber range, Reality Bridge | World manifest, isolation and bridge contracts | W01, W03, W06 | Simulation/real boundary and fidelity model |
| W08 Surfaces & distribution | Browser, JARVIS, terminal, device, edge/cloud/offline | Surface bridge and placement contracts | W01, W02, W05 | No surface-side authority |
| W09 Security & assurance | Threat model, key custody, audit, privacy, supply chain | Trust-zone, key and audit decisions | W01, W03 | Security invariants and incident recovery |
| W10 Domain fabrics | Health, legal, finance, science, engineering, environment, etc. | Domain manifests and escalation policies | W06, W09 | Domain-specific validity and human review |
| W11 Performance & operations | Budgets, SLOs, telemetry, capacity, fairness | Resource/SLO contract | W05, W08 | Bounded, measurable operational envelope |
| W12 Product & ecosystem | Marketplace, community, business, financial rails | Domain boundary and trust contracts | W09, W10 | Explicit non-authority and ledger boundaries |

## Parallelization rules

- Workstreams may draft independently only where their shared interfaces are already named.
- Any change to identity, authority, state ownership, semantic schema or runtime lifecycle is cross-stream and requires a decision record.
- No stream may invent a second canonical principal, execution ID, action envelope, provenance object or policy epoch.
- Shared terms are defined once in the canonical glossary/contract registry; local documents link to it.
- A source path may be cited as an implementation anchor, but its presence does not count as contract satisfaction.
- Conflicting proposals are recorded as alternatives; do not silently reconcile by changing code.
- Keep all changes in architecture documents on the existing draft branch.

## Fast closure method

1. Resolve B0 decisions in W01–W04 as a dependency cluster.
2. Resolve W05–W09 in parallel against the frozen authority/runtime/state contracts.
3. Resolve W10–W12 with explicit deferred scopes where specialist evidence is not yet available.
4. Run a documentation consistency pass: terminology, plane mapping, IDs, schemas, owners, lifecycle and failure states.
5. Produce one signed-off Architecture Freeze Manifest listing accepted ADRs, unresolved deferred items, source paths, contract versions and excluded implementation work.
6. Only after explicit freeze approval begin integration; only after integration begin comprehensive verification.

## Status vocabulary

- **DRAFTED:** document exists; content may still conflict.
- **SOURCE-RECONCILED:** source anchors and ownership have been reviewed.
- **DECIDED:** an ADR records the chosen architecture and alternatives.
- **DEFERRED:** explicitly outside the current freeze, with reason and owner.
- **FROZEN:** approved contract version; changes require a new ADR.
- **IMPLEMENTED:** code path exists and is traceable to a frozen contract.
- **VERIFIED:** evidence demonstrates stated acceptance criteria for a specific commit/configuration.

A workstream cannot jump from DRAFTED to FROZEN. IMPLEMENTED and VERIFIED are separate states.

## Current cycle disposition

- W02 runtime topology: ADR-002 proposed; source reconciliation partial.
- W03 state/recovery: ADR-003 proposed; namespace and persistence inventory incomplete.
- W04 agent fabric: ADR-004 proposed; native/operational call-site inventory incomplete.
- W05 routing/resource placement: ADR-005 proposed; provider-fabric boundary inventory incomplete.
- W01, W06–W12: remain active and are tracked in the architecture decision backlog.
- No implementation or verification is authorized by this coordination document.


## Expanded discovery protocol — current cycle

The three new governing documents now extend all twelve streams:
- System-wide gap register: classifies missing, ambiguous, duplicate, conflicting, orphaned, unbounded, unverified, stale, unsupported, unsafe-fallback, hidden-coupling and governance gaps.
- Operational lifecycle/trust architecture: makes bootstrap, enrollment, key custody, policy/configuration evolution, upgrade, offline/partition, recovery, incident and decommission first-class concerns.
- Cryptographic agility/MIF architecture: treats cryptography as an existing cross-cutting source family requiring full caller/custody reconciliation; MIF remains within P18 and does not change the canonical 18-plane count.

### Current disposition after this expansion

- W01/W09: lifecycle and cryptographic trust contracts drafted; exact callers, custody providers, root recovery, algorithm inventory and revocation freshness remain un-reconciled.
- W02/W03: runtime/state topology proposals exist; full entrypoint, persistence, journal namespace, migration and recovery-consumer inventories remain open.
- W04/W05: agent-fabric and routing proposals exist; direct invocation, delegation, lease, result admission, budget and placement enforcement inventories remain open.
- W06: NEXUS/FRL/MIF evidence architecture expanded; canonical schemas, source lineage, checker trust and semantic equivalence remain open.
- W07/W08: MIRROR WORLD and surface/distribution architecture remains active; fidelity, bridge authorization, offline reconciliation and surface lifecycle require source review.
- W10/W11/W12: domain, operations and ecosystem discovery continues; domain validity, SLO/capacity, tenant/billing/community governance require explicit manifests and owners.

Discovery is concurrent; acceptance of dependent contracts remains ordered by authority and shared schema decisions. All new documents are proposals, not frozen decisions. No implementation, integration, test campaign, merge or deployment is authorized.


## Source-reconciliation status update — W01–W05

A bounded inspection of main at 7d900bc75843ea968aa5886d251dbfac83a5d93c is recorded in NORYX7_SOURCE_RECONCILIATION_W01_W05.md. It inspected identity, policy, multi-authorization, replay guard, three runtime facades, state/store journal, native/operational agent fabrics, supervisor, agent router, provider router/gateway/resilience and resource-tier router.

- W01: DISCOVERED/MAPPED in part. Local in-memory identity and signed-approval registries are confirmed; durable principal/agent/device authority, root recovery and global revocation freshness remain unresolved.
- W02: DISCOVERED/MAPPED in part. NORYXRuntime, HypersynthRuntime and OperationalNORYXRuntime overlap; canonical entrypoint and complete constructor/call-site graph remain unresolved.
- W03: DISCOVERED/MAPPED in part. StateStore/StateJournal local commit and recovery contracts are inspected; all journal namespaces, external witnesses, migrations and cross-store recovery remain unresolved.
- W04: DISCOVERED/MAPPED in part. Native AgentFabric direct run path and OperationalAgentFabric supervisor/admission path are confirmed; complete call-site and authority graph remains unresolved.
- W05: DISCOVERED/MAPPED in part. Agent selection, provider routing and device/edge/cloud tier routing are distinct source components; composed retry, idempotency, capacity, residency and cost rules remain unresolved.
- W06–W12: architecture documents and discovery obligations exist; source reconciliation is still open and must continue in parallel.

The source review is bounded, not exhaustive. These streams cannot be marked DECIDED or FROZEN. No runtime changes, test campaigns, integration, merge or deployment are authorized.


## Source-reconciliation status update — W06–W12

A bounded inspection of main at 7d900bc75843ea968aa5886d251dbfac83a5d93c is recorded in NORYX7_SOURCE_RECONCILIATION_W06_W12.md.

- W06: DISCOVERED/MAPPED in part. Typed task/result contracts, verification, Universal Intelligence evidence/domain assessments, context and in-memory memory store are confirmed. Canonical NEXUS ontology, source lineage, epistemic model and proof/empirical separation remain open.
- W07: DISCOVERED/MAPPED in part. Synthetic sandbox-only CyberRange, sandbox lifecycle, seeded evaluation campaigns and adversarial scenarios are confirmed. Universal world models, calibration, holdout governance and Reality Bridge remain open.
- W08: DISCOVERED/MAPPED in part. Offline states/snapshot protocols, distributed topology metadata, in-memory device fabric and JARVIS runtime bridge are confirmed. Concrete offline providers, monotonic/revocation freshness, conflict resolution and full surface call graph remain open.
- W09: DISCOVERED/MAPPED in part. DefenseGate, secure boot chain and signed artifact manifest verification are confirmed. Root provisioning, build provenance, key rotation/revocation and single gate ownership remain open.
- W10: DISCOVERED/MAPPED in part. Universal Intelligence declares domain routing and budgets; complete domain-specific manifests and expert governance are not established by this inspection.
- W11: DISCOVERED/MAPPED in part. Runtime limits, bounded security event bus, alert routing and provider retry wrappers exist; fleet-wide SLO, telemetry, capacity, fairness and incident recovery remain open.
- W12: DISCOVERED/MAPPED in part. Global memory and identity authorization indexes are in-memory structures; durable transport/storage, governance, billing and community/product lifecycle remain open.

All W01–W12 now have bounded source-reconciliation records, but none is closed. Continue deeper call-site, adapter, deployment and domain-manifest discovery. No implementation, test campaign, integration, merge or deployment is authorized.


## Deep source-reconciliation status — 2026-11-22

New bounded source record: `NORYX7_DEEP_SOURCE_RECONCILIATION_ALL_WORKSTREAMS.md`.

- W01: additional agent mission, device identity/capability and agent liveness sources found; principal taxonomy, issuer, trust roots and revocation remain open.
- W02: CanonicalSystemFabric, ExecutionFabric, RuntimeEngine and ControlPlane reveal a material composition-root ambiguity. ADR-002 must not be frozen before caller graph closure.
- W03: runtime in-memory signed journal, core SQLite journal, recovery epoch machine and SQLite monotonic anchor confirmed as distinct mechanisms. Durable reservation and restore ordering remain open.
- W04: AgentMesh, AgentRuntime and AgentCoordinator add separate discovery/liveness/coordination layers; all direct dispatch call sites remain to be inventoried.
- W05: execution adapter, egress allowlist, device capability gate, provider/agent/resource routers and scheduler require explicit authority and enforcement boundaries.
- W06: architecture_registry structural completeness must be distinguished from system-wide architecture closure.
- W07: generic ExecutionFabric adapters do not themselves constitute a calibrated MIRROR WORLD or safe Reality Bridge.
- W08: offline adapters and local monotonic anchor require concrete provider, anti-rollback and sync/revocation mapping.
- W09: ControlPlane, Defense, Recovery, egress, SecureBoot and supply chain need one end-to-end trust chain.
- W10: domain packages need physical safety and jurisdictional validity manifests.
- W11: seven CI workflow definitions found; deployment source of truth, release promotion and disaster recovery still need explicit mapping.
- W12: marketplace, payment, internal ledger and community contribution governance must remain distinct from execution authority.

All twelve remain PARTIAL. This pass does not authorize code changes, integration or test campaigns.


## Polyglot surface reconciliation — 2026-11-22

New bounded source record: `NORYX7_POLYGLOT_SURFACE_AND_JARVIS_AUTHORITY_RECONCILIATION.md`.

- W01: map gateway client_id, JARVIS user principal, JARVIS workload/agent identity and iOS device identity into a single principal/device/workload taxonomy.
- W02: JARVIS composes RuntimeEngine, CanonicalSystemFabric and JarvisRuntimeBridge; this is a concrete composition path that must be reconciled with the proposed SRC.
- W03: JARVIS request-state reservation/commit and RuntimeEngine step-attestation journal are separate stores; cross-store atomicity/recovery remains open.
- W04: JARVIS front-end/orchestrator/registry, NORYX operational agent fabric and provider adapters need a single call graph and ownership map.
- W05: provider gateway/resilience and Go/Rust service boundaries need composed retry, digest, authorization and dispatch semantics.
- W08: Python gateway, Android browser, Android audio bridge, iOS adapter and TypeScript UI are separate surfaces with distinct lifecycle/credential boundaries.
- W09: gateway HMAC secret, workload signing key, device grants, TLS and artifact signatures need purpose-separated key custody and revocation contracts.
- W11: Render Python service does not define release/deployment of Go/Rust/mobile/browser artifacts; multi-artifact lifecycle remains open.
- W12: client enrollment, tenant identity, provider onboarding, billing and support require governance beyond gateway session creation.

All affected workstreams remain partial. No source code, dependency, test, integration or deployment changed.
