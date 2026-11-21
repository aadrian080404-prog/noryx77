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
