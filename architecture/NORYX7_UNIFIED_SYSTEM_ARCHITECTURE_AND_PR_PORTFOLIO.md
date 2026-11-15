# NORYX7 — Unified System Architecture and Parallel PR Build Plan

**Status:** architecture baseline / implementation inventory, not a claim of completed implementation  
**Baseline:** `main` at `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Prepared:** 2026-11-15  
**Scope:** NORYX7, HYPERSYNTH AI, JARVIS interaction, device/edge/cloud fabric, security, memory, runtime, network, data, SURF, finance, governance and critical infrastructure.

## 1. Purpose and truth model

This document is the single architecture map for parallel construction. It does not mark a component implemented merely because a directory, interface, design note, or PR exists. Every component must carry one of these states:

- **DESIGNED** — contract and threat model documented.
- **GENERATED** — code drafted but not yet integrated or tested.
- **IMPLEMENTED** — executable implementation exists in a branch.
- **INTEGRATED** — connected to its canonical runtime and contracts.
- **TESTED** — focused deterministic tests pass.
- **VERIFIED** — required CI, adversarial tests, security review and integration gates pass.
- **DEPLOYED** — deployed in a stated environment with operational evidence.

A PR is a delivery unit, not proof of production readiness. Open PRs are not part of `main` until reviewed and merged. No claim of global scale, impenetrability, certified safety, or production readiness follows from local tests.

## 2. System thesis and invariants

NORYX7 is a local-first, device-sovereign, federated agentic operating fabric — not a chatbot wrapper or social feed.

### 2.1 Devices are the distributed substrate

The protected devices remain sovereign endpoints. They may optionally contribute compute, storage, memory or bandwidth to a federated fabric, but protection must never depend on contribution.

- Contribution is explicit opt-in, purpose-scoped, resource-capped and revocable.
- The owner controls battery, thermal, power, data, network, schedule and energy ceilings.
- Local protection and essential operation continue offline.
- No hidden mining, background workload, implicit enrollment or forced resource sharing.
- Revocation is persisted before workload teardown; the target resource enforces monotonic fencing/generation checks.
- Device telemetry is treated as time-bounded evidence, not unquestionable truth.
- Nodes are not trusted merely because they belong to the network.

### 2.2 Distributed topology

1. **Device plane:** local agents, protected resources, local policy, local encrypted memory, local execution boundary.
2. **Personal edge plane:** user-controlled nearby devices and optional home/office nodes.
3. **Regional/domain plane:** federated coordinators for bounded domains and failure regions.
4. **Cloud/remote plane:** optional high-capacity inference, archival and specialist services.
5. **Federation control plane:** signed policy/configuration/identity metadata, capability discovery and revocation distribution.

No global consensus is required for every action. Consensus and quorum are partitioned by resource, tenant, domain and risk. Local safety decisions must fail closed when required evidence is missing. A remote coordinator cannot silently override local owner policy.

## 3. Canonical architecture layers

| Layer | Responsibility | Primary contracts / boundaries |
|---|---|---|
| L0 Device & OS | device identity, sensors, lifecycle, secure boot, OS isolation | device identity, trusted telemetry, platform capabilities |
| L1 Interface | Android/browser/desktop/web/voice/visual interaction | interaction envelope, session identity, consent |
| L2 Gateway & API | ingress, sessions, rate limits, protocol translation | authenticated request, tenant, request ID |
| L3 Identity & Trust | user/device/agent/service identities, attestation, revocation | principal, identity epoch, trust evidence |
| L4 Authorization & Policy | least privilege, consent, risk classification, capabilities | action plan digest, capability grant, policy decision |
| L5 HYPERSYNTH cognitive kernel | understanding, decomposition, reasoning, planning, metacognition | task graph, hypothesis, evidence, bounded budget |
| L6 Agent Fabric | specialist agents, delegation, collaboration, supervision | agent identity, role, task lease, result provenance |
| L7 Model Fabric | local/edge/cloud model routing, provider isolation, fallback | model capability, data classification, route decision |
| L8 Tool & Execution Fabric | tools, sandbox, process lifecycle, external side effects | tool manifest, action permit, execution receipt |
| L9 Memory & Knowledge | L0–L5 memory, retrieval, causal replication, offline knowledge | memory event, provenance, retention, causal clock |
| L10 Data Fabric | object storage, content addressing, integrity, replication | object manifest, chunk digest, encryption/key reference |
| L11 Matrix / Network Fabric | membership, placement, resource grants, messaging, fencing | node admission, grant generation, reservation, envelope |
| L12 Audit & Verification | evidence chain, witnesses, tests, evaluations, rollback detection | audit event, signed receipt, checkpoint, verification report |
| L13 SURF / Systems Understanding | static inspection, protocol/system mapping, authorized reverse engineering | scope authorization, evidence record, finding confidence |
| L14 Business & Financial Fabric | accounting, budgets, transfers, marketplace settlement adapters | ledger posting, idempotency key, compliance decision |
| L15 Governance & Critical Infrastructure | human oversight, safety interlocks, institutional access | risk class, quorum approval, one-shot permit |
| L16 Observability & Self-Healing | metrics, traces, diagnosis, recovery, safe rollback | health signal, incident, recovery plan, change authorization |

Cross-cutting requirements: privacy/data minimization, provenance, secure supply chain, resource budgets, localization, accessibility, offline-first behavior and deterministic testability.

## 4. HYPERSYNTH AI architecture (first-class workstream)

The AI is not a single prompt or model. It is a controlled cognitive runtime composed of independently testable stages:

1. **Input understanding:** classify intent, entities, context, uncertainty, language and user consent.
2. **Context assembly:** retrieve only authorized memory and data; attach provenance and freshness.
3. **Decomposition:** produce a typed TaskGraph with bounded depth, fan-out, time, token, cost and tool budgets.
4. **Hypothesis generation:** create alternative plans and identify assumptions and missing evidence.
5. **Reasoning / lateral exploration:** explore branches in isolated, bounded workspaces; no branch gains authority by generating a proposal.
6. **Simulation and prediction:** run deterministic tools, digital twins or sandboxed experiments where suitable.
7. **Independent verification:** challenge claims, verify evidence, check invariants and compare alternative outcomes.
8. **Metacognition:** assess confidence/calibration and identify when to abstain or ask for missing input. Self-assessment is not proof.
9. **ActionGate:** classify risk using trusted policy, bind approval to the complete plan digest, target, parameters, expiry and identity epoch.
10. **Execution:** use least-privilege, killable, sandboxed executors; validate target-side fencing immediately before side effects.
11. **Consensus / review:** use independent agents only where risk warrants; do not count multiple personas backed by the same model/credential as independent witnesses.
12. **Audit and learning:** append outcome receipts; learning is idempotent, evidence-backed, bounded and reversible.

### AI subdomains and deliverables

- Cognitive kernel: task graph, planner, reasoning, hypothesis ledger, bounded branch scheduler.
- Agent Fabric: specialist registry, delegation, identity binding, collaboration, supervisor, result validation.
- Model Fabric: capability-based routing, local-first inference, provider adapters, cost/privacy routing, failover and circuit breakers.
- Memory intelligence: working/episodic/semantic/procedural memory, L0–L5 hierarchy, retrieval evaluation, forgetting/retention policy, causal replication.
- User understanding: explicit preference/context model, uncertainty, consent, correction and deletion workflows.
- Multimodal: text, image, audio, video and sensor inputs with modality-specific provenance and authorization.
- Evaluation: task success, factuality, calibration, robustness, latency, cost, privacy leakage and regression suites.
- Self-improvement: proposal-only changes, independent evaluation, signed artifact provenance, staged rollout and rollback. No self-modification of authorization or safety roots.

## 5. Workstream inventory and PR portfolio

The repository already contains substantial foundations and many open PRs. The current GitHub search returned 63 open PRs, including Matrix (#73), system inspection (#72/#69/#60/#50), runtime/sandbox (#71/#68/#62/#53/#45/#27), memory (#70/#59/#58/#55/#54/#52/#47/#42/#37), audit/witnesses (#66/#65/#63/#61/#57/#49/#41/#40/#38), agent identity (#64/#48/#46/#31/#26), execution/audit (#56/#33), key lifecycle (#51/#43/#32/#29), and earlier security/SURF foundations (#23–#22, #21–#16, #8, #7). This list is a snapshot, not a statement that those PRs are merged or CI-green.

The following portfolio defines the missing/remaining work. Before opening a PR, compare its exact paths and contracts with all open PRs and existing code; extend an existing branch where appropriate rather than duplicate it.

| Portfolio ID | Domain | Scope to build / complete | Depends on |
|---|---|---|---|
| P00 | Architecture inventory & contracts | file/PR ownership map, canonical API schemas, dependency graph, status ledger | none |
| P01 | Identity & trust | user/device/agent/service identities, enrollment, attestation adapters, revocation propagation | P00 |
| P02 | Authorization & policy | capability lifecycle, risk taxonomy, plan-bound grants, consent, delegation and revocation | P00, P01 |
| P03 | HYPERSYNTH kernel | typed TaskGraph, bounded planning, hypothesis/evidence ledger, branch isolation, verification gates | P00–P02 |
| P04 | Agent Fabric | specialist roles, delegation, independent challenge, agent lifecycle and supervisor | P01–P03 |
| P05 | Model Fabric | local/edge/cloud routing, provider contracts, model capability registry, privacy/cost routing | P03 |
| P06 | Memory & knowledge | L0–L5 lifecycle, encryption, retrieval, causal sync, offline corpus and retention | P01, P02 |
| P07 | Runtime & execution | canonical runtime, sandbox, process tree control, deadlines, cancellation, recovery | P01, P02 |
| P08 | Tool & browser interface | tool manifests, browser isolation, navigation/interaction, voice, desktop/device adapters | P02, P07 |
| P09 | Matrix node fabric | opt-in membership, resource grants, budget, reservation, placement, supervisor, fencing | P01, P02 |
| P10 | Network & messaging | authenticated envelopes, peer discovery, transport security, replay/DoS limits, partition recovery | P01, P09 |
| P11 | Data & storage | encrypted objects, content addressing, replicas, integrity proofs, retention and restore | P01, P06, P10 |
| P12 | Audit & verification | append-only event chain, external witnesses, receipts, CI gates, adversarial evaluation | P01, P02, P07 |
| P13 | SURF / reverse engineering | authorized scope, static parsers, protocol mapping, evidence provenance, safe dynamic lab adapters | P02, P07, P12 |
| P14 | Digital Twin & simulation | deterministic virtual time, fault injection, network partitions, resource and workload models | P09–P12 |
| P15 | Self-healing & resilience | detection, diagnosis, bounded repair proposals, canary, rollback and recovery | P07, P12, P14 |
| P16 | Finance & business fabric | double-entry ledger, idempotent transfer adapters, budget controls, settlement/compliance boundaries | P01, P02, P12 |
| P17 | Governance & institutions | human oversight, institutional access, separation of duties, transparency and appeals | P01, P02, P12 |
| P18 | Critical infrastructure | safety classification, dual control, local interlocks, target-side permit enforcement and certified-controller adapters | P02, P07, P12, P17 |
| P19 | Observability & operations | metrics, traces, health, incident response, fleet rollout, SLO and cost controls | all runtime domains |
| P20 | Android / NORYX Browser | hardened WebView, permissions, download/content boundaries, navigation, local AI handoff | P01, P02, P07, P08 |
| P21 | Social contribution & ecosystem | trusted information, anti-bot signals, community projects, ethical supply-chain evidence and marketplace | P01, P02, P06, P12, P16, P17 |
| P22 | Integration & release | compatibility matrix, end-to-end contracts, migration, signed release and staged deployment | P00–P21 |

### Parallel construction rule

Build workstreams in parallel after P00 defines stable contracts. Use independent branches for non-overlapping domains; where shared files are unavoidable, nominate one owner branch and integrate through a reviewed contract change. No parallel writes to the same file. Every PR includes focused tests and explicit non-goals. Large work is split into reviewable vertical slices, not placeholder packages.

## 6. Shared contracts (versioned, canonical)

All domains must converge on the following common envelope shapes. Exact Python/JSON schemas are to be added in P00 and validated against implementations; names below are semantic contracts, not existing code guarantees.

- **Principal:** `principal_id, principal_type, tenant_id, identity_epoch, trust_evidence_ref`.
- **RequestEnvelope:** `request_id, correlation_id, principal, issued_at, expires_at, payload_digest, data_classification`.
- **TaskGraph:** `task_id, graph_digest, parent_id, dependencies, objective, constraints, budget, risk_class, provenance_refs`.
- **CapabilityGrant:** `grant_id, subject, resource, actions, scope, constraints, generation, expires_at, issuer, revocation_ref`.
- **PolicyDecision:** `decision_id, allow/deny, policy_version, evaluated_subject, action_digest, reasons, expiry`.
- **ExecutionIntent:** `intent_id, task_id, plan_digest, target, capability_ref, fencing_generation, idempotency_key`.
- **ExecutionReceipt:** `receipt_id, intent_digest, executor_identity, start/end, result_digest, exit_status, sandbox_profile, evidence_refs`.
- **MemoryEvent:** `event_id, actor, entity, vector_clock, payload_digest, encryption_key_ref, provenance, retention_class`.
- **DataManifest:** `object_id, schema_version, chunk_digests, total_size, encryption_metadata, owner, integrity_proof_ref`.
- **AuditEvent:** `sequence, event_type, actor, subject, payload_digest, previous_digest, signature_ref, timestamp`.
- **NodeEnvelope:** `node_id, owner_id, membership_epoch, grant_generation, resource_budget, telemetry_timestamp, attestation_ref`.
- **Error:** stable machine-readable code, retryability, safe public detail, diagnostic reference; never leak secrets.
- **ChangeProposal:** immutable diff digest, author, threat analysis, test evidence, independent approvals, rollout and rollback plan.

Every schema must define canonical serialization, versioning, unknown-field behavior, size limits, timestamp rules, signature coverage and migration policy. Reject ambiguous encodings and non-finite numeric values.

## 7. Security and trust architecture

- Deny by default; fail closed for missing, stale, malformed or unverifiable authorization evidence.
- Separate identity, authentication, authorization, policy, execution and audit authorities.
- No component may authorize itself or provide the only evidence of its own correctness.
- Bind approvals to the full immutable plan/action digest, not a task label or caller assertion.
- Revalidate identity, policy, grant generation, expiry and fencing at the target side immediately before side effects.
- Use monotonic epochs and idempotency keys; make replay, downgrade and stale-worker behavior explicit.
- Keep key material outside metadata registries; use injected KMS/HSM boundaries and rotation/revocation protocols.
- Treat local SQLite as local durability, not distributed consensus or independent witness quorum.
- Sandbox untrusted code and data; static inspection must not execute samples.
- Distinguish test doubles, local simulations, independent deployments and production trust domains.
- For critical infrastructure, this system only coordinates policy and permits; certified local safety controllers and physical interlocks remain authoritative.

## 8. Integration sequence (one architecture, staged execution)

**Wave A — Map and freeze contracts:** inventory paths, tests, imports, PR ownership, branch bases and current CI; publish schema registry and compatibility policy.

**Wave B — Build independent domains:** AI kernel, identity/policy, memory, runtime, Matrix, SURF, data, audit, finance, browser and governance advance in parallel against versioned contracts.

**Wave C — Vertical integrations:** AI → Agent Fabric → Model Fabric → Memory/Tools → ActionGate → Runtime → Audit; separately Device → Matrix → Network → Data → Digital Twin; join via identity, policy, events and audit.

**Wave D — Adversarial integration:** stale identity, revoked grants, replay, crash/restart, partial commit, partitions, malicious peers, malformed data, model/provider failure, prompt injection, tool abuse, resource exhaustion and rollback.

**Wave E — Release qualification:** reproducible build, dependency and supply-chain checks, full CI, security review, migration/restore drill, staged canary, observability and rollback evidence.

The “single cycle” means one coordinated architecture and portfolio, not a single giant unreviewable PR or one simultaneous merge. Integration tests begin as soon as shared contracts exist; the final system-wide verification is performed after the vertical slices converge.

## 9. Definition of done for every PR

1. Exact scope, owner domain, dependencies and non-goals stated.
2. No duplicate implementation or conflicting contract.
3. Input validation, bounds, timeouts and resource ceilings.
4. Authorization and identity revalidation at side-effect boundary.
5. Deterministic unit and adversarial tests.
6. Restart, replay, concurrency and failure-path tests where applicable.
7. Audit/provenance for security-relevant state transitions.
8. No secrets, unsafe defaults, hidden network egress or implicit device contribution.
9. Focused CI and full relevant workflow evidence recorded by commit SHA.
10. Integration compatibility and explicit remaining production gates.

## 10. Initial repository inventory — known, not yet exhaustive

The default branch already contains broad foundations under `core/`, `architecture/`, `tests/`, `android/` and related directories. Notable core areas include agent/runtime/identity, HYPERSYNTH, planning/reasoning/metacognition, memory hierarchy, device/distributed fabrics, execution, policy, audit, sandbox, recovery, providers, offline operation, SURF/system inspection and supply-chain checks.

The current open-PR set contains overlapping generations of work. PR #73 is a Matrix Core draft; PRs #69/#72/#60/#50 contribute system-inspection slices; #71/#64/#48 and related branches address agent identity; #70/#59/#55 address causal memory; #68/#62/#53/#45/#27 address sandbox/runtime; #66/#65/#63/#61/#57/#49/#41/#40/#38 address audit/witnessing. These must be reconciled by changed-path and dependency analysis before any replacement PR is created.

The former architecture manifest PR #11 is closed without merge. Its content must not be treated as present on `main`. The inventory and contract map in this document are the replacement baseline, and the actual file/branch/PR reconciliation remains a required P00 task.

## 11. Safety and branch policy

- Never push directly to `main`.
- Never alter `architecture-freeze-2026-09-06`.
- Keep PRs draft until focused tests and review evidence justify readiness.
- Do not merge automatically.
- Fetch current file/blob and branch SHAs immediately before every update.
- Never force-push to shared work branches.
- Keep Matrix contribution opt-in and local-first.
- Report exact tested commit, command/workflow, result and limitations.
- Mark unverified or blocked work honestly; do not convert plans into implementation claims.

## 12. Immediate next execution tasks

1. Complete P00: enumerate every open PR, branch head, changed path, CI status and merge base; inventory all tracked files and test entry points.
2. Reconcile the current Matrix, AI/runtime, memory, security, SURF and audit branches into a dependency graph.
3. Publish versioned contracts and ownership map.
4. Create or extend the remaining domain PRs in parallel without duplicating existing work.
5. Add cross-domain end-to-end tests as soon as each contract is implemented.
6. Maintain a live status ledger with per-component state from Section 1.

**This document is the unified architecture and PR portfolio. It is not a declaration that all portfolio components have already been implemented.**
