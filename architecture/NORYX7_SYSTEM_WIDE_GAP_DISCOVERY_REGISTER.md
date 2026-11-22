# NORYX7 — System-wide architecture gap discovery register

**Status:** active discovery baseline; architecture-only; not a completeness claim  
**Parent:** System-wide Architecture Closure / PR #212

## 1. Purpose

The architecture cannot be declared complete merely because every known plane has a document. Discovery must also find capabilities absent from the initial decomposition, overlapping implementations, hidden authority paths, missing lifecycle states and operational conditions that emerge across subsystem boundaries.

The cryptographic inventory is a concrete example: the repository already contains crypto boundaries, envelope encryption, key lifecycle, secure channel, identity, attestation, trust-chain and multi-authorization components. Finding these later means the original architecture map was not sufficiently exhaustive. The response is not to bolt on an isolated crypto feature; it is to repeat discovery systematically across every plane and cross-cutting domain.

This register controls discovery and reconciliation. It does not claim that every listed source has been exhaustively read or that proposed contracts are implemented.

## 2. Independent status axes

**Architecture status:** UNKNOWN, DISCOVERED, MAPPED, CONTRACTED, DECIDED, DEFERRED, FROZEN.

**Implementation/evidence status:** ABSENT, PRESENT, PARTIAL, UNASSESSED, VERIFIED. VERIFIED is permitted only with evidence tied to an exact commit, configuration, environment and acceptance scope.

Never collapse these axes. A present implementation can be architecturally unmapped; a contracted capability can be absent from code; a green test can verify only a narrow behavior.

## 3. Gap taxonomy

| Code | Class | Meaning |
|---|---|---|
| G01 | Missing | Required capability or lifecycle step has no identified owner/design |
| G02 | Ambiguous | Responsibility, term, state or boundary admits multiple interpretations |
| G03 | Duplicate | Multiple components claim the same canonical responsibility |
| G04 | Conflict | Contracts or authorities contradict one another |
| G05 | Orphan | Component, data, API, job or surface has no owning lifecycle |
| G06 | Unbounded | Work, storage, retries, fan-out, cost, time or privilege lacks a hard bound |
| G07 | Unverified | Claim lacks required evidence; not proof that code is defective |
| G08 | Stale | Contract, schema, key, model, policy or artifact can outlive validity |
| G09 | Unsupported | Required environment, mode, failure or interoperability case is not covered |
| G10 | Unsafe fallback | Failure can silently become success, permissive behavior or ambiguous state |
| G11 | Hidden coupling | Dependency on implicit call path, global state or undocumented ordering |
| G12 | Governance gap | Approval, accountability, ownership, retention or escalation is undefined |

## 4. Twelve parallel workstreams — discovery obligations

| Stream | Domain | Required discovery beyond current ADRs | Main gap classes |
|---|---|---|---|
| W01 | Identity, trust and authority | Human, service, agent, device, workload and tenant principals; enrollment, binding, delegation, consent, policy epochs, revocation, emergency authority, break-glass and trust-root recovery | G01–G05, G08, G10, G12 |
| W02 | Runtime topology | Every process entrypoint, coordinator, engine, facade, worker, plugin host, JARVIS lifecycle, startup/shutdown, upgrade and compatibility path | G02–G05, G11 |
| W03 | State, data and recovery | All stores, journals, caches, checkpoints, event streams, snapshots, replicas, migrations, retention, erasure, restore and uncertain external side effects | G01–G06, G08–G10 |
| W04 | Agent fabric | Every agent type and invocation path, capability manifest, trust binding, lease, delegation, supervision, collaboration, cancellation and result admission | G02–G06, G10–G11 |
| W05 | Routing and resources | Provider/model choice, agent allocation, task scheduling, placement, dispatch, quotas, reservations, fairness, backpressure and cost accounting | G02, G04, G06, G11 |
| W06 | Semantics, knowledge and evidence | NEXUS schemas, ontology, canonicalization, source lineage, claims, uncertainty, contradiction, temporal validity, formal proof and scientific evidence | G01–G04, G07–G09 |
| W07 | MIRROR WORLD | Synthetic web, cyber range, software models, digital twins, physical/environmental/economic worlds, simulation fidelity, experiment isolation and Reality Bridge | G01–G04, G06–G10 |
| W08 | Surfaces and distribution | Browser, voice, multimodal, terminal, mobile, desktop, API, edge/cloud/offline, session handoff, local authority and synchronization | G02–G06, G08–G11 |
| W09 | Security and assurance | Cryptographic boundaries, key custody, secure boot, attestation, channel security, authorization replay, audit, threat model, incident response and supply chain | G01–G10, G12 |
| W10 | Domain fabrics | Health, law, finance, science, engineering, agriculture, ecology, climate, education, logistics and public-interest/community domains | G01–G04, G07–G09, G12 |
| W11 | Performance and operations | SLOs, capacity, telemetry, quotas, queueing, overload, degradation, fairness, cost, deployment, upgrades, incident and disaster recovery | G01–G06, G08–G10 |
| W12 | Product and ecosystem | Tenant lifecycle, marketplace, integrations, financial rails, billing, metering, community projects, contributor identity, governance and dispute handling | G01–G05, G08–G12 |

All streams progress concurrently. Dependencies constrain contract acceptance, not discovery: a stream may record a dependency before its upstream decision is frozen.

## 5. Cross-cutting capability checklist

Search for these across all planes, not only in modules whose names suggest them:

1. Identity, authentication, authorization, delegation, consent and revocation.
2. Cryptography, key custody, key rotation, algorithm agility, secure boot, attestation and trust recovery.
3. Data classification, privacy, tenant isolation, retention, deletion, export, residency and replica reconciliation.
4. Provenance, evidence, epistemic state, source independence, temporal validity and audit integrity.
5. Formal methods, proof checking, theorem/counterexample handling, scientific validation and model fidelity.
6. Multimodal ingestion, transformation, alignment, spatial/time coordinates and original-artifact preservation.
7. Human oversight, approvals, emergency stop, appeal, accountability and operator separation.
8. Supply-chain integrity for source, dependencies, builds, models, datasets, plugins and update channels.
9. Scheduling, quotas, budgets, metering, fairness, overload, backpressure and graceful degradation.
10. Federation, discovery, interoperability, protocol/schema negotiation, offline operation and conflict resolution.
11. Observability, audit, alerting, incident response, forensics, backup, restore and disaster recovery.
12. Self-improvement, configuration/policy evolution, staged rollout, rollback and immutable trust roots.
13. Product lifecycle: onboarding, setup, account recovery, support, billing, portability, deletion and exit.
14. Domain validity: jurisdiction, standards, units, uncertainty, expert review and prohibited inferences.
15. Physical-world safety: device capabilities, actuator bounds, fail-safe states, environmental conditions and human override.
16. Accessibility, localization, usability, user comprehension and consent UX.

## 6. Mandatory questions for every component

For every source file, service, API, agent, tool, store, job, surface, model or domain package, record:

- What need does it serve, and what is out of scope?
- Is it code, configuration, schema, documentation, fixture, adapter or external dependency?
- Who owns its lifecycle? Which plane is primary and which are secondary?
- Who may invoke it, under what identity, scope, consent and capability?
- What are its inputs, outputs, side effects and canonical identifiers?
- Which schemas, versions, units, canonicalization rules and provenance are required?
- Which state does it own, read, mutate, replicate or cache?
- What are startup, shutdown, expiry, cancellation and upgrade semantics?
- What happens on timeout, partial completion, duplicate request, crash, partition and uncertain acknowledgement?
- Which limits bound CPU, memory, tokens, fan-out, storage, retries, time and money?
- What is observable and audited, and what sensitive data must not be logged?
- What are the threat, abuse, misuse and safety cases?
- How is it isolated, backed up, restored, migrated and decommissioned?
- What is its compatibility and deprecation contract?
- What measurable evidence would later establish contract satisfaction?

## 7. Repository discovery protocol

The source inventory must include more than obvious source modules:

1. Full tracked tree: source, tests, docs, examples, scripts, migrations, schemas, assets and generated files.
2. Build/runtime manifests: packaging, Android/Gradle, lockfiles, containers, build definitions and toolchains.
3. CI/CD and automation: workflows, release pipelines, secret references, permissions, artifact retention and deployment configuration.
4. Entry points and invocation graph: imports alone are insufficient; trace constructors, factories, registries, callbacks, CLI/API routes, event handlers and background workers.
5. Persistence and external I/O: databases, files, caches, queues, network clients, subprocess boundaries, device APIs and third-party providers.
6. Configuration and environment: defaults, precedence, secret injection, feature flags, tenant settings and unsafe fallback behavior.
7. Tests and fixtures: evidence of intended behavior, not proof that untested paths or production deployments are complete.
8. Existing architecture references: reconcile overlapping and historical documents; preserve provenance and identify stale claims.
9. Product requirements: include capabilities described in plans even when no implementation path exists.
10. External dependencies: trust, availability, licensing, data handling, versioning and exit strategy.

Search results and filename matches are discovery leads, not exhaustive proof. Every source review records inspected ref/commit, paths and scope.

## 8. Closure evidence per workstream

A workstream is not closed until it has:
- complete source/capability inventory with explicit inspected scope;
- one primary owner per responsibility and documented shared contracts;
- authority, identity and trust dependencies mapped;
- canonical data, state and event lifecycles;
- normal, failure, degraded, cancellation and recovery paths;
- threat, privacy, safety and abuse cases;
- bounded resource and operational assumptions;
- versioning, compatibility, migration and deprecation rules;
- explicit decisions or deferred items with owner and rationale;
- traceability from requirements to components to later acceptance criteria.

No 100% score is permitted while any in-scope category remains UNKNOWN. DEFERRED is transparent, not equivalent to complete.

## 9. Current cycle findings and priorities

ADR-002 through ADR-005 remain proposals. Unresolved evidence includes runtime call-site/constructor inventory, all persistence namespaces and recovery consumers, every direct agent invocation, and provider/placement ownership.

The source traceability ledger identifies crypto-related families including core/crypto.py, core/key_lifecycle.py, core/secure_channel.py, core/identity.py, core/attestation.py, core/trust_chain.py, core/secure_boot.py, core/multiauth.py, core/authorization_replay.py, core/security_integration.py, core/secure_memory.py and core/secure_storage.py. This is a discovery inventory only. It does not establish complete key custody, algorithm agility, rotation under partition, trust-root recovery, certificate lifecycle, hardware-backed protection or post-quantum migration.

The next reconciliation cycle must treat W01/W09 cryptographic authority and trust lifecycle, W02/W03 runtime-state lifecycle, W04/W05 invocation/resource lifecycle, and W06 evidence/semantic lifecycle as coupled design clusters while continuing W07–W12 discovery in parallel.

## 10. Freeze prohibition

Architecture freeze is prohibited while an in-scope plane or cross-cutting capability is UNKNOWN; a source family is unclassified; authority or state ownership is contradictory; a required failure/recovery path is undefined; a critical assumption has no owner/disposition; traceability is broken; or the architecture depends on unbounded or implicit behavior.

This register does not authorize integration, implementation, testing, deployment or merge. Those phases begin only after explicit architecture-freeze approval.

## Additional gaps discovered — 2026-11-22

| Gap | Class | Evidence anchor | Required closure |
|---|---|---|---|
| G-INGRESS-01 | conflicting / ambiguous | `web/app.py`: direct `/api/chat` vs gateway-authenticated `/v1/execute` | Route-by-route canonical ingress/auth policy and upstream enforcement evidence |
| G-CONTEXT-01 | unbounded trust / incomplete provenance | `jarvis/context/authorized.py` | Versioned source manifest, tenant/purpose scope, consent, classification, retention and attestation |
| G-OBSERVATION-01 | unverified / stale evidence | `jarvis/observation/fabric.py` | Trusted capture time, monotonic sequence, digest/signature, freshness and anti-replay |
| G-PERCEPTION-01 | authority ambiguity | `jarvis/perception/audio.py` | Keep wake event separate from identity, explicit user intent and ActionGate authorization |
| G-CONSENT-01 | incomplete lifecycle | `core/user_understanding.py` | Durable purpose-specific consent, inference lineage, correction, deletion and tombstones |
| G-CYBER-01 | weak authorization evidence | `core/cyber_range.py` | Signed owner authorization and independent Reality Bridge policy gate |
| G-DEVICE-01 | local-only selection | `core/device_fabric.py` | Attested enrollment, leases, revocation, capacity/residency-aware selection |
| G-DISTRIBUTED-01 | declared-not-proven security | `core/distributed.py` | Cryptographic shard manifest, key custody, replication and anti-rollback |
| G-SCALE-01 | in-memory control-plane primitive | `ecosystem/global_scale.py` | Durable queue, atomic capacity lease, fencing, deduplication and reconciliation |
| G-PROVIDER-01 | underspecified adapter contract | `jarvis/providers/base.py` | Versioned typed provider contract, usage, privacy, timeout, cancellation and idempotency |

These are architecture discovery findings, not test-proven defects.
