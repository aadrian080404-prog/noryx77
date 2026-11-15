# NORYX7 — Complete System Architecture Blueprint

**Status:** canonical architecture specification (DESIGNED); not an implementation or verification claim.  
**Parent baseline:** PR #74, branch `architecture/noryx7-unified-system-map-2026-11-15`, commit `7b32de6eb76a9a50b685eabc7d62d2015e02757e`.  
**Scope:** complete target architecture for the NORYX7 cognitive operating system, HYPERSYNTH, sovereign device fabric, runtime, security, data, applications and ecosystem.

## 0. Architecture constitution

NORYX7 is a **device-sovereign, local-first, federated cognitive operating system**. It is not an LLM, chatbot, prompt wrapper or a single central server. It coordinates cognition, agents, memory, tools, compute, storage, communications, policy and applications as one governed runtime.

HYPERSYNTH is the cognitive kernel. Language models are replaceable inference providers behind Model Fabric; they do not own identity, memory, policy, execution authority, system state or the control plane. The OS must remain useful in degraded/offline mode through local models, deterministic software, cached knowledge, domain agents and explicit capability reduction.

The system is self-managing but not sovereign over its owners. It may observe, plan, allocate within granted budgets, recover, optimize and propose changes. It cannot silently enroll devices, expand its privileges, rewrite trust roots, bypass owner policy, or approve its own high-risk actions.

### Non-negotiable invariants

1. Device owner sovereignty: contribution is opt-in, scoped, metered, revocable and never required for local protection.
2. Local-first privacy: data stays on the originating device unless a user/policy explicitly authorizes a transfer.
3. Least privilege: every side effect is bound to an authenticated principal, capability, policy decision and immutable action digest.
4. Offline continuity: essential local functions do not depend on cloud inference or global consensus.
5. Fail-safe degradation: missing identity, stale policy, invalid evidence or exhausted budgets reduce capability or deny action.
6. Evidence over assertion: model output, confidence scores and agent consensus are not proof.
7. Reversibility: upgrades, learned policies and self-healing changes are staged, auditable and rollback-capable.
8. Explicit trust boundaries: devices, peers, providers, models, plugins, files, sensors and external services are untrusted until validated.
9. No hidden resource extraction: no covert compute, storage, bandwidth, battery or data contribution.
10. Interoperability without lock-in: providers and transports are adapters; canonical contracts remain NORYX-owned and versioned.

## 1. System topology and planes

### 1.1 Planes

- **Device plane:** Android, desktop, laptop, server, embedded/edge nodes; local UI, local policy enforcement, secure storage, sensors and execution isolation.
- **Personal edge plane:** user-controlled home/office devices and private gateways.
- **Federated domain plane:** optional regional, organizational or project clusters with bounded membership and failure domains.
- **Remote service plane:** optional cloud inference, external search, archival and specialist services.
- **Control plane:** signed configuration, identity epochs, membership, capability discovery, policy distribution, revocation and software release metadata.
- **Data plane:** encrypted object transfer, event replication, task dispatch, inference and tool execution.
- **Evidence plane:** audit chains, signed receipts, test/evaluation records, provenance and independent witnesses.

The control plane must not be able to silently seize the data plane. Local policy remains authoritative for local resources. A partitioned node may continue permitted local work while refusing operations that require unavailable remote evidence.

### 1.2 Node classes

A node can expose one or more independently granted roles: endpoint, personal edge, compute worker, storage replica, relay, coordinator, witness, domain service or offline archive. Role is not trust. Admission and permissions are separate decisions.

Each node publishes a signed, privacy-minimized capability manifest: hardware/software capabilities, supported protocols, resource ceilings, availability window, security posture and software measurement where available. Sensitive device inventory is not globally broadcast.

### 1.3 Resource lifecycle

`DISCOVERED → ENROLLED → ATTESTED → ELIGIBLE → GRANTED → RESERVED → ACTIVE → REVOKING → DRAINED → RELEASED`

Every transition has an owner, timestamp, epoch, evidence and audit event. Revocation increments a monotonic generation before dispatch is stopped; workers must reject stale generations at the resource boundary. Reservations expire automatically. No task may exceed CPU, memory, disk, network, battery, thermal, energy, time or monetary budgets.

## 2. Canonical layered architecture

| Layer | Name | Primary components |
|---|---|---|
| L0 | Hardware & OS | secure boot/keystore adapters, OS sandbox, sensors, lifecycle, power/thermal monitors |
| L1 | Experience | Android, desktop, web, browser, voice, visual and accessibility interfaces |
| L2 | Gateway & sessions | API gateway, session manager, protocol adapters, rate limits, request validation |
| L3 | Identity & trust | user/device/agent/service identity, enrollment, attestation, epochs, revocation |
| L4 | Policy & authorization | consent, capability grants, risk engine, policy evaluation, approval and delegation |
| L5 | HYPERSYNTH | context, decomposition, hypotheses, planning, branching, simulation, metacognition |
| L6 | Agent Fabric | specialist registry, scheduler, delegation, collaboration, supervisor, agent lifecycle |
| L7 | Model Fabric | local/edge/cloud model routing, capability registry, provider adapters, fallback |
| L8 | Tool & execution | tool registry, action gate, sandbox, process executor, browser automation, cancellation |
| L9 | Memory & knowledge | working/episodic/semantic/procedural memory, retrieval, retention, offline knowledge |
| L10 | Data Fabric | encrypted object store, content addressing, chunking, integrity, replication, backup |
| L11 | Matrix & network | membership, resource market, placement, reservations, peer transport, messaging |
| L12 | Evidence & assurance | audit, verification, witnesses, policy evidence, evaluation, incident response |
| L13 | SURF | system/software/protocol inspection, dependency graph, authorized reverse engineering |
| L14 | Simulation | digital twins, virtual clock, fault injection, workload and network simulation |
| L15 | Resilience | health, diagnosis, repair proposals, canary, failover, recovery and rollback |
| L16 | Finance & ecosystem | budgets, ledger, settlement adapters, marketplace, contribution accounting |
| L17 | Governance & safety | separation of duties, human oversight, appeals, critical-system interlocks |
| L18 | Operations | telemetry, SLOs, deployment, configuration, fleet management, support |

Cross-cutting services: cryptography/key lifecycle, privacy, provenance, schema registry, localization, accessibility, supply-chain security, quotas and compatibility management.

## 3. HYPERSYNTH cognitive kernel

### 3.1 Cognitive pipeline

`RECEIVE → UNDERSTAND → CONTEXTUALIZE → DECOMPOSE → HYPOTHESIZE → PLAN → EXPLORE → SIMULATE → VERIFY → DECIDE → AUTHORIZE → EXECUTE → OBSERVE → LEARN`

Each stage is a typed, bounded module. A stage may return `SUCCESS`, `PARTIAL`, `NEEDS_EVIDENCE`, `NEEDS_APPROVAL`, `DENIED`, `BUDGET_EXHAUSTED` or `FAILED`; no stage may silently convert failure into success.

### 3.2 Core subsystems

- Intent and context interpreter: task type, entities, constraints, user goal, ambiguity and consent.
- Context assembler: authorized memory retrieval, source freshness, provenance and data classification.
- TaskGraph compiler: typed DAG with dependencies, invariants, budgets, risk class and acceptance tests.
- Hypothesis ledger: alternatives, assumptions, falsifiable predictions, evidence and status.
- Planner: deterministic and model-assisted planning, bounded search, dependency scheduling and replanning.
- Lateral exploration: isolated branches with explicit resource/time/fan-out ceilings; branches produce proposals, never permissions.
- Simulation broker: selects deterministic tests, sandbox experiments, digital twins or external evidence.
- Verifier: schema, provenance, factual evidence, invariants, independent challenge and test receipts.
- Metacognition: uncertainty decomposition, calibration, contradiction detection, abstention and request for missing evidence.
- ActionGate: risk classification, policy decision, human approval and plan-digest-bound capability.
- Outcome learner: idempotent, privacy-preserving, evidence-backed updates with versioning and rollback.

### 3.3 TaskGraph contract

Required fields: `task_id, graph_id, graph_version, objective, nodes[], edges[], constraints[], acceptance_criteria[], risk_class, budget, owner_principal, provenance_refs[], created_at, expires_at`.

Each node carries `node_id, operation, input_schema, output_schema, dependencies[], required_capabilities[], data_classification, timeout, retry_policy, idempotency_key`. Graphs are immutable after authorization; replanning creates a new graph digest and invalidates approvals for changed actions.

### 3.4 Budget dimensions

Depth, fan-out, wall time, CPU, memory, tokens, provider spend, tool calls, network bytes, storage, energy and external side effects. Budgets are reserved before work and reconciled after. Unknown provider cost is not zero; it is unknown and requires a conservative reservation or denial.

## 4. Agent Fabric

Components: agent registry, signed manifests, role/capability catalogue, scheduler, task leases, delegation manager, collaboration protocol, supervisor, health monitor, result validator and retirement manager.

Every agent has a stable identity, software version, declared tools, model/provider lineage, allowed data classes, resource budget and policy scope. Agents receive scoped task leases, not ambient authority. Delegation cannot widen the parent grant. Agent results include task digest, input provenance, execution receipts, model lineage and limitations.

Primary/secondary critique using the same model/provider is **same-provider self-critique**, not independent consensus. Independent corroboration requires distinct evidence or trust domains and an explicit independence assessment. A quorum counts identities only when their independence assumptions are justified.

## 5. Model Fabric

Model Fabric is a replaceable inference subsystem, not the cognitive OS. It provides:
- capability and modality discovery;
- local-first route selection with privacy classification;
- model/provider adapter isolation;
- policy-aware fallback and circuit breakers;
- bounded request/response sizes, timeouts, retries and cancellation;
- usage/cost/latency metering with unknown values represented honestly;
- prompt/data classification and redaction;
- model lineage and response provenance;
- offline deterministic fallback and graceful unavailability.

No model receives execution authority or direct access to secrets. Structured outputs are schema-validated and treated as untrusted proposals. Tool calls must be reinterpreted and authorized by NORYX7, not executed because a model requested them.

## 6. Identity, cryptography, policy and authorization

### 6.1 Principals

Principal types: user, device, agent, service, organization, workload and external provider. Identity records include immutable identifier, issuer, key references, identity epoch, lifecycle state, allowed authenticators and revocation evidence.

### 6.2 Capability grants

A grant binds subject, resource, actions, scope, constraints, data classes, generation, expiry, issuer and parent grant. Delegation is attenuating only: child permissions are a strict subset of parent permissions. Revocation is monotonic and checked at the side-effect target, not just at request ingress.

### 6.3 Risk tiers

- R0: read-only local deterministic operations.
- R1: reversible local changes within user-approved scope.
- R2: external communication, data transfer or financial/resource commitment.
- R3: sensitive personal, organizational or high-impact operations.
- R4: critical infrastructure, physical safety, irreversible or systemic impact.

Approval thresholds, independent reviewers and local interlocks increase with risk. R4 is not autonomously executed by a general-purpose agent; certified local controllers and physical safety systems remain authoritative.

### 6.4 Key management

Keys are generated, stored, rotated, revoked and recovered through platform keystore/KMS/HSM adapters. Applications receive opaque key handles, not raw root keys. Key lifecycle metadata is durable and authenticated. A local database is not an independent remote witness. Recovery requires threshold policy and audit; no universal master key.

## 7. Runtime, execution and tool fabric

Canonical composition root builds the configured runtime from validated configuration and injected interfaces. No module should construct a shadow runtime with different security defaults.

Execution lifecycle:
`PROPOSED → VALIDATED → AUTHORIZED → RESERVED → DISPATCHED → RUNNING → COMMITTED`
with terminal alternatives `DENIED, EXPIRED, CANCELLED, FAILED, ROLLED_BACK`.

Before dispatch and again at the target: validate identity epoch, grant generation, policy version, plan digest, expiry, idempotency, budget and target binding. Executors enforce deadlines, process-tree termination, output bounds, filesystem/network policy and cancellation. Side-effect adapters must expose prepare/commit or compensating actions where possible.

Tool manifests declare input/output schemas, side effects, risk tier, capabilities, network domains, resource ceilings, timeout, idempotency and audit requirements. Browser automation is isolated from credentials and untrusted page content; page text is data, never policy.

## 8. Memory, knowledge and user context

### 8.1 Memory classes

- Working: short-lived active task context.
- Episodic: user-authorized events and interaction history.
- Semantic: validated facts, concepts and relationships with provenance.
- Procedural: tested workflows and reusable skills.
- System: versioned architecture/configuration knowledge.
- Evidence: immutable or append-only audit and verification receipts.

L0–L5 is a placement/retention hierarchy, not a substitute for semantic memory classes. Each record has owner, tenant, purpose, classification, provenance, creation/expiry, retention, encryption key reference and deletion state.

### 8.2 Session separation

Conversation/session ID, execution ID, task ID, agent ID and tenant/owner ID are distinct. Cross-turn retrieval requires explicit session scope and user policy. Global unscoped memory is forbidden. Forget/delete operations propagate to replicas and derived indexes according to documented retention law, with tombstones and audit proofs where legally appropriate.

### 8.3 Knowledge and offline mode

Offline knowledge packs are signed, versioned, source-attributed and updateable. Search/retrieval reports source dates and uncertainty. Cached data is not presumed current. Knowledge ingestion treats documents, web pages, images and tool outputs as untrusted data; prompt injection cannot change system policy.

## 9. Data Fabric

Object lifecycle: ingest → classify → validate → encrypt → chunk → address → replicate (if granted) → verify → retain/archive/delete. Use content digests, canonical manifests, authenticated encryption, per-owner key scopes, integrity verification and resumable transfers. Replication policy is based on data classification, owner consent, jurisdiction and replica trust. Backups are tested by restore drills; replication is not backup.

## 10. Matrix, networking and distributed compute

### 10.1 Matrix control services

Membership authority, node registry, capability discovery, resource grant manager, scheduler/placement, reservation ledger, workload dispatcher, health supervisor, revocation/fencing service and reconciliation engine.

### 10.2 Resource grant

A resource offer declares resource type, maximum quantity, availability window, energy/battery/thermal ceiling, permitted workload classes, data locality, compensation policy, expiry and revocation endpoint. The owner may pause or revoke at any time. The scheduler cannot treat advertised capacity as guaranteed until reservation succeeds.

### 10.3 Distributed execution

Tasks are partitioned by data locality and failure domain. Use signed envelopes, mutual authentication, replay protection, quotas, backpressure and bounded queues. Workloads are idempotent or have explicit deduplication/compensation. Nodes report receipts, not self-certified truth. A Byzantine or compromised node must not gain authority from its participation.

### 10.4 Partition and consensus policy

Local owner policy works without quorum. Quorum is scoped to a specific decision and membership epoch; it must not be global by default. During partitions, deny or defer actions requiring unavailable quorum, while allowing safe local tasks. No split-brain writes to authoritative ledgers; use fencing epochs and explicit conflict resolution.

## 11. Network, messaging and external connectivity

Adapters for HTTPS/mTLS, QUIC or other reviewed transports, local IPC and optional peer discovery. All messages carry version, sender identity, recipient/scope, nonce, issue/expiry, payload digest and signature/MAC. Enforce size, rate, replay and decompression limits. DNS, redirects, certificates and destination allowlists are policy-controlled. No unrestricted SSRF or hidden egress.

## 12. Audit, verification and assurance

Audit events are append-only, sequence-bound and hash-linked; signatures and external anchors provide tamper evidence. Audit must not log secrets or unnecessary personal data. Record authorization decisions, key transitions, grants/revocations, execution intents/results, data transfers, model lineage, configuration changes and recovery.

Verification layers: schema validation; unit/property tests; deterministic integration; concurrency/crash/replay tests; adversarial tests; static analysis; dependency/SBOM/signature checks; independent review; staging canary; production telemetry. Every evidence record names commit SHA, environment, test command, timestamp and result. A passing test is evidence only for the tested scope.

## 13. SURF — System Understanding & Reverse Engineering Fabric

SURF is a first-class, permission-bound analysis subsystem for software, operating systems, devices, protocols, APIs and observable system behavior.

Pipeline: authorize target/scope → acquire evidence → fingerprint safely → parse statically → build dependency/call/data-flow graph → map protocol/state machine → identify assumptions and attack surface → formulate hypotheses → reproduce in isolated lab → verify finding → report confidence and remediation.

Static parsers must never execute untrusted samples. Dynamic analysis runs only in a disposable, network-restricted sandbox with explicit authorization. Findings include target/version, collection method, hashes, scope, reproducibility, confidence, false-positive caveats and responsible disclosure status. SURF must not copy proprietary source or bypass access controls; the goal is interoperable understanding and defensive assessment.

## 14. Digital Twin and simulation fabric

Provides deterministic virtual time, synthetic devices, topology/network models, resource schedulers, fault injection, workload replay and state snapshots. Simulations label assumptions and model fidelity; they are not evidence of real-world safety unless validated against real measurements. Supports chaos campaigns for partitions, latency, packet loss, node loss, clock skew, disk full, thermal throttling and provider failure.

## 15. Self-management, self-healing and controlled evolution

The OS continuously observes health, budgets, drift, security signals and SLOs. It may:
1. detect anomaly;
2. collect evidence;
3. isolate affected component if policy permits;
4. create a bounded repair proposal;
5. run tests and threat analysis in isolation;
6. obtain required approvals;
7. deploy canary;
8. verify health;
9. promote or rollback;
10. publish an audit record.

No autonomous update may modify root identity, trust anchors, authorization invariants, audit deletion rules or safety interlocks. A failed repair cannot recursively broaden its own permissions. Learning and configuration changes are versioned, attributable and reversible.

## 16. Applications and product surfaces

All surfaces use the same authenticated session and canonical runtime:
- NORYX Browser: privacy-preserving browsing, isolated page context, local AI handoff, download controls and anti-tracking policy.
- Android/device agent: local protection, permissions, sensors, resource consent and offline mode.
- Desktop/workspace: file/app automation through explicit tool manifests and user approval.
- Voice/vision: modality-specific consent, visible capture state, local processing preference and retention policy.
- Enterprise/domain console: roles, tenants, policy, audit, budgets and deployment.
- Developer SDK/API: typed contracts, capability-scoped plugins, sandbox and compatibility guarantees.

A surface is not a separate intelligence stack. It is an interface to the same OS services.

## 17. Finance, marketplace and contribution economy

Financial functions are separated from cognitive planning and execution. Core services: double-entry ledger, account/ownership model, budget reservation, settlement adapters, idempotency, reconciliation, fraud controls, tax/compliance boundary and dispute handling.

Community contribution records distinguish money, time, materials, compute, storage and services. Resource contribution is voluntary; reward/compensation rules are transparent and appealable. Marketplace listings require identity, provenance, quality and dispute processes. No wallet or payment adapter may bypass authorization, audit or legal compliance. Financial integrations begin in sandbox mode.

## 18. Governance, social information and community services

Governance services provide transparent policy versions, delegated roles, separation of duties, appeals, public evidence summaries and incident disclosure. Information integrity features label source provenance, date, corroboration and uncertainty; bot/fake-account detection emits probabilistic signals, not identity accusations. Community project modules can coordinate cleanup, repair, recycling, local production and mutual aid while minimizing personal data and preventing coercive labor or opaque scoring.

Ethical supply-chain analysis stores sourced claims, confidence and remediation status; allegations are not treated as facts without evidence and due process.

## 19. Critical infrastructure and physical systems

NORYX7 may provide monitoring, planning, simulation and policy coordination, but safety-critical control remains with certified local controllers, hardware interlocks and trained operators. Use dual control, explicit operating envelopes, fail-safe states, independent sensor validation, immutable logs and tested manual override. No LLM or general agent directly controls hazardous actuators.

## 20. Observability and operations

Standardize structured logs, metrics, traces, health checks, audit events and privacy budgets. Operational dashboards cover availability, latency, error rates, queue depth, resource usage, provider spend, energy, replication lag, policy denials, security incidents and rollback state. Alerts must include evidence and runbooks. SLOs are declared per service and environment; no global uptime claim without measurements.

## 21. Canonical cross-domain contracts

Every schema is versioned and defines canonical serialization, size limits, time semantics, unknown-field behavior, signature coverage and migration policy.

- `Principal`: principal_id, type, tenant, identity_epoch, issuer, trust_refs.
- `Session`: session_id, owner, tenant, consent_scope, created_at, expires_at, retention_policy.
- `RequestEnvelope`: request_id, correlation_id, principal, session_ref, issued_at, expires_at, payload_digest, classification.
- `TaskGraph`: graph_id, version, digest, nodes, edges, constraints, budgets, risk, provenance.
- `CapabilityGrant`: grant_id, subject, resource, actions, scope, constraints, generation, expiry, parent_ref.
- `PolicyDecision`: decision_id, allow/deny, policy_version, subject, action_digest, reasons, expiry.
- `ExecutionIntent`: intent_id, graph_digest, plan_digest, target, capability_ref, fencing_generation, idempotency_key.
- `ExecutionReceipt`: receipt_id, intent_digest, executor, timestamps, result_digest, exit_status, sandbox, evidence.
- `MemoryEvent`: event_id, owner, session/task, actor, vector_clock, payload_digest, key_ref, provenance, retention.
- `DataManifest`: object_id, schema_version, chunks, total_size, encryption, owner, integrity_proof.
- `NodeEnvelope`: node_id, owner, membership_epoch, grant_generation, resource_budget, telemetry_time, attestation.
- `AuditEvent`: sequence, type, actor, subject, payload_digest, previous_digest, signature_ref, timestamp.
- `ChangeProposal`: diff_digest, author, threat_model, test_evidence, approvals, rollout, rollback.

## 22. Failure semantics and recovery

Every service declares startup dependencies, readiness criteria, liveness criteria, retryability, timeout, circuit-breaker behavior, durable state, recovery procedure and safe degraded mode. Retries require idempotency. A crash between prepare and commit is recovered from a durable journal. Unknown commit state is reconciled, never blindly repeated. Recovery is tested under process kill, power loss, disk exhaustion, clock rollback, key rotation and network partition.

## 23. Repository implementation map

Map logical domains to existing code before adding packages; exact paths are owned by the P00 inventory and must be verified against current branches.

| Domain | Existing candidate areas | Required integration result |
|---|---|---|
| Cognitive kernel | `core/hypersynth*`, planning, reasoning, metacognition | canonical typed task graph and stage contracts |
| Agents | `core/agent*`, collaboration, operational fabric | identity-bound agents and attenuating delegation |
| Models | `noryx7_runtime/model_fabric.py`, adapters, `core/llm` | provider-neutral inference with provenance/metering |
| Runtime | `core/runtime.py`, operational runtime, gateway | single composition root and side-effect enforcement |
| Security | identity, policy, action gate, key lifecycle, sandbox | target-side authorization and revocation fencing |
| Memory | memory hierarchy, secure memory, causal replication | session/tenant scopes, encryption, retention and offline sync |
| Matrix | Matrix/resource/membership branches | owner-controlled grants, reservations and revocation |
| Audit | audit log, durable journal, witness branches | tamper-evident receipts and crash recovery |
| SURF | system inspector, ELF/Python/protocol analysis | authorized evidence-based analysis pipeline |
| Interfaces | gateway, Android, browser, desktop, voice | all surfaces use canonical sessions/runtime |
| Operations | bootstrap, health, workflows, telemetry | reproducible deployment, SLOs and rollback |
| Ecosystem | finance, marketplace, governance, community | isolated bounded services with compliance and audit |

## 24. Architecture completion gates

The architecture is considered **specification-complete** only when:
- every domain has purpose, ownership, boundaries, threat model and lifecycle;
- all cross-domain contracts have schemas and compatibility rules;
- every side effect has identity, policy, capability, budget, idempotency and audit semantics;
- device sovereignty, offline behavior, partition handling and revocation are specified;
- failure/recovery and data lifecycle are specified;
- product surfaces map to canonical services;
- unresolved assumptions and non-goals are recorded;
- a traceability matrix maps every requirement to implementation paths, tests and evidence.

The implementation is considered **integrated** only after canonical composition and end-to-end tests pass. It is **verified** only after required adversarial, security, recovery, compatibility and CI evidence is attached to exact commits. It is **deployed** only with environment-specific operational evidence.

## 25. Immediate build sequence

1. P00: exhaustive path/PR/branch/test inventory, ownership and overlap graph.
2. Freeze shared schema registry and versioning rules.
3. Build/fix the canonical composition root and session identity.
4. Build parallel vertical slices for HYPERSYNTH, Agent/Model Fabric, identity/policy, memory, execution/audit, Matrix/network/data, SURF/simulation, interfaces, finance/governance and operations.
5. Integrate by contracts, not by blind branch merging.
6. Run focused tests on each slice, then end-to-end and adversarial campaigns.
7. Publish a traceability matrix with explicit DESIGNED/IMPLEMENTED/INTEGRATED/TESTED/VERIFIED/DEPLOYED states.

**Important:** this blueprint completes the target architecture specification, not the software implementation. Existing PRs, code and tests must be reconciled and verified before any domain can be marked integrated or complete.
