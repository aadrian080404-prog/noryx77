# NORYX7 Architecture Build & Verification Manifest

Status: architecture planning and traceability baseline
Date: 2026-11-13

## 1. Purpose

This document is the single index for preparing the complete NORYX7 / HYPERSYNTH architecture before repeatedly implementing isolated fragments. It reduces duplicated design work by defining component boundaries, contracts, dependencies, acceptance evidence and PR batches.

A generated file, interface, placeholder, mock, simulation or design note is not an implemented production capability. Every component must carry an explicit lifecycle state:

- specified: purpose, threat model, inputs/outputs and invariants defined.
- generated: source or schema generated, not yet reviewed.
- implemented: executable behavior exists.
- integrated: intended production call paths use it; no parallel bypass remains.
- tested: deterministic unit, integration, negative and fault-injection tests pass.
- independently_verified: evidence reviewed by a verifier not controlled by the component under test.
- production_qualified: operational, security, recovery, privacy, performance and deployment evidence accepted for a defined environment.

Never promote a component automatically between states. A test fixture, in-memory adapter or synthetic campaign cannot qualify a production capability.

## 2. Complete architecture inventory

This is a planning index, not a claim that every domain is implemented. Existing repository files must be mapped to each component during inventory.

### A. Foundation and contracts
Typed contracts: Intent, TaskGraph, Plan, HypothesisSet, Evidence, ProofBundle, JournalEntry, MemoryEntry and ExecutionContext. Domain-bound contracts: CriticalInfraAction, FinancialTransaction, CognitiveDecision, DecoyInteraction, OSINTQuery, SovereignRequest and PaymentIntent. Include schema versioning, canonical serialization, strict bounds, provenance and explicit unknown/denied states. Invariants: no implicit trust, fabricated success, boolean-only proof or unbounded payloads.

### B. Identity, trust and authorization
Principal and agent identity; key ownership and lifecycle; device/workload identity; attestation; capability/role/attribute policy; deny-by-default action gate; transaction/context binding; one-shot durable authorization; replay resistance; revocation; expiry; delegation; separation of duties; independent verifier identities and signed receipts. Test identity substitution, confused deputy, replay, escalation, stale grants and verifier self-certification.

### C. Cryptography and privacy
Key derivation and domain separation; authenticated encryption; MAC/signature verification; rotation and revocation; external key custody (KMS/HSM/secure element) and recovery; privacy boundaries, minimization, compartmentalization and controlled disclosure. PQC migration follows stabilization of core identity/state contracts; no home-grown cryptography.

### D. State, journal and persistence
One authoritative durable state model across core/state_journal.py and noryx7_runtime/state.py. Authenticated append-only records, sequence binding, chain continuity, external monotonic anti-rollback anchor, crash consistency, idempotent append, partial-commit recovery, corruption quarantine, explicit legacy migration, backup/restore, encryption at rest, concurrent writers and disaster recovery. Test tampering, truncation, rollback, torn writes, duplicate commits, split-brain and key loss.

### E. Memory L0-L5 and Global Memory Fabric
Memory tiers, promotion/demotion, provenance, expiry, deletion, retrieval and conflict handling; encrypted local/distributed storage; tenant/agent isolation; consistency and replication contracts. Test memory poisoning, stale memory, cross-context recall, leakage and rollback. Global memory is not a distributed persistent service until the actual service exists.

### F. Cognition and HYPERSYNTH orchestration
Perception/context acquisition; task decomposition; bounded planning; hypothesis generation/falsification; Cognitive Cells, Global Workspace, Thalamic Gate and predictive/metacognitive mechanisms only where operational contracts and measurable tests exist; tool/model routing, resource budgets, confidence calibration, uncertainty and dissent. Separate model output, observed fact, inference and verified claim.

### G. Planning, task graph and execution
Typed DAG, dependency/cycle validation, resource/deadline budgets, cancellation and idempotency; planning, simulation, policy preflight, execution, result admission and recovery; partial completion, retries, compensating actions, uncertain outcomes and rollback. No task claims success without verified postconditions.

### H. Metacognition and learning
Outcome measurement, calibration, contradiction detection, error taxonomy and bounded adaptation. Learn from verified defensive successes and failures as well as attacks. No self-modification of policy, verifier, trust roots or authorization thresholds without independent approval. Preserve provenance, rollback and reproducible evaluation sets.

### I. Runtime assurance and resource orchestration
Runtime monitor, process isolation, executor cancellation, sandbox boundaries and resource accounting; device/edge/cloud routing with explicit data residency and trust boundaries; scheduling, quotas, backpressure, failover and recovery. GlobalScale/autoscaling is not live until adapters, metrics, safety limits and fault tests exist.

### J. Adversarial defense and security testing
Entity classes × power tiers × techniques × surfaces × objectives × difficulty; isolated red/blue policies; capability budget per simulated entity; replay, tamper, substitution, escalation, sandbox escape, exfiltration, corruption, supply-chain and denial-of-service cases; deterministic reproduction, unique IDs, seeds, artifacts, coverage and regression minimization. Synthetic counts must be separated from live executions and externally validated incidents. No tests against third-party systems without explicit authorization.

### K. SURF and authorized system understanding / reverse engineering
Static architecture recovery: imports, dependency graph, call paths, data flows, schemas, trust boundaries and bypass paths. Dynamic observation only on owned or explicitly authorized targets, with scoped authorization and sandbox receipts. Evidence-backed hypotheses, differential experiments, reproducible traces and independent verification. No copying proprietary code or circumvention outside authorization.

### L. Deception and moving-target defense
Honeytokens, decoys, isolated deception environments, rotation and telemetry. Deception events never become trusted evidence without provenance and verification. Containment and response must be policy-gated, reversible where possible and audited.

### M. OSINT and external intelligence
Source provenance, freshness, corroboration, confidence, licensing and privacy boundaries. Separate public information from inferred identity or sensitive data. No autonomous action based solely on unverified external intelligence.

### N. Communications and distributed infrastructure
Secure transport, mutual authentication, replay protection, key rotation and downgrade resistance; mesh/edge connectivity, intermittent links, offline operation and conflict resolution. LoRa, BLE, Wi-Fi CSI, optical/acoustic channels and specialized links remain optional adapters until threat-modeled and tested. Use BFT/consensus only where a concrete trust/failure model requires it.

### O. Financial and institutional systems
Payment intent, authorization, idempotency, ledger consistency, settlement/reconciliation and dispute handling. Compute credits and marketplace accounting remain separate from the core security trust model. Institutional gateway: mandate, jurisdiction, necessity, proportionality, M-of-N approval, least disclosure, audit and revocation. Predicate proofs establish only formally defined properties; they do not establish legal truth or guarantee non-retention of disclosed data.

### P. Device, hardware and energy
Device enrollment, secure boot/attestation, key custody, update chain and recovery; edge compute, resource scheduling, power/thermal constraints and storage integrity. Hardware-rooted guarantees require actual supported hardware and adversarial validation; software simulation is not equivalent.

### Q. Governance, safety and operations
Separation of technical custody, authorization, verification and governance; change control, incident response, key compromise, emergency stop and continuity; audit retention, privacy/legal review, supply-chain security, release signing and rollback. Kill switches and dead-man mechanisms require explicit failure analysis and cannot depend on one person or secret.

## 3. Mandatory implementation order

The first eight workstreams are gates. Later work may be specified in parallel but must not bypass these dependencies:

1. Types, canonical serialization and proof contracts.
2. Identity, trust roots and transaction-bound authorization.
3. Unified authenticated state journal and crash/rollback recovery.
4. Memory L0-L5 with provenance and isolation.
5. Planning and TaskGraph with bounded execution semantics.
6. Metacognition, uncertainty and controlled learning.
7. Runtime assurance, cancellation, sandbox and recovery.
8. Adversarial campaigns, independent verification and regression gates.

After these gates: PQC migration, external APIs, advanced deception, OSINT, institutional gateway productionization, payments, hardware-specific functions, Xenos and Noesis.

Architecture domains may be specified and dependency-reviewed in parallel. Implementation follows the dependency graph; no speculative module is connected to privileged execution just to make the architecture appear complete.

## 4. PR batching strategy

Use small, reviewable, dependency-aware PRs. Do not create empty PRs or one enormous PR with unrelated changes.

- PR-A: architecture inventory, contracts index, status schema and dependency graph.
- PR-B: identity and authorization integration.
- PR-C: authenticated journal, anchor protocol and crash recovery.
- PR-D: memory L0-L5 persistence and isolation.
- PR-E: planning, task graph and execution semantics.
- PR-F: metacognition, verifier independence and bounded learning.
- PR-G: runtime assurance, cancellation and sandbox integration.
- PR-H: adversarial campaign engine, stratification, artifacts and regression minimization.
- PR-I: SURF authorized observation and system-understanding workflow.
- PR-J onward: separate PRs for deception, OSINT, communications, institutional, financial, hardware and governance adapters.

Each PR declares exact base SHA and dependency PRs; lists changed contracts, call sites and trust boundaries; includes positive, negative, boundary, concurrency and fault-injection tests as relevant; runs focused tests before full CI; includes migration/rollback for persistent formats; states limitations and non-implemented features; and remains unmerged until required checks and review gates pass.

Avoid concurrent PRs editing the same core contracts or journal files. Parallelize independent analysis and test design; serialize writes to shared foundations.

## 5. Verification and evidence gates

For every component collect:
- Static: types, dependency graph, unsafe API scan, secret scan, dead code and unreachable/bypass paths.
- Unit: normal, invalid, boundary, malformed and adversarial inputs.
- Integration: all callers, serialization boundaries, identity and authorization propagation.
- Concurrency: races, duplicate requests, replay and ordering.
- Fault injection: process kill, disk full, I/O failure, network partition, timeout, key unavailable and partial commit.
- Security: attacker capability, privilege boundary, data exposure, rollback and recovery.
- Performance: latency, memory, CPU, storage growth and bounded worst-case behavior.
- Independent review: verifier not controlled by implementation under test.
- Reproducibility: exact commit, environment, seed, commands, logs and artifacts.

A green CI result means only that checks actually run passed on that exact commit. It is not a security certification or proof of zero vulnerabilities.

## 6. Scenario campaign reporting

The existing 10-million upper bound and 9 × 7 entity/power strata are campaign capacity, not proof that ten million live attack/defense executions occurred.

Report separately: configured maximum; generated cases; executed cases; completed cases; unique scenarios; stratum coverage; assertions evaluated; failures and minimized reproductions; live sandbox runs; independently verified outcomes; runtime and resource cost.

Use deterministic sharding and resumable artifacts. Never count skipped, rejected, duplicate or merely generated scenarios as executed successful tests.

## 7. Current integration checkpoint

At authoring time:
- PR #11 contains the multi-sector tranche and 10M campaign workstream.
- The branch contains scenario stratification, adversarial-intelligence contracts, journal-integrity proof scaffolding and SURF contract hardening.
- HMAC proof helper is not yet integrated into the SQLite state journal.
- External monotonic anchor is an interface/test implementation, not a production remote or hardware anchor.
- Adversarial intelligence remains bounded scaffolding, not independent trained red/blue agents.
- 10M maximum is not evidence of a completed 10M live campaign.
- Institutional access remains a policy gate, not a production data-release system.
- SURF still needs authorized live observation adapters and independently verifiable sandbox receipts.

Refresh this checkpoint from the repository before each release; it is not a live status dashboard.

## 8. Completion definition

NORYX7 is not complete because every planned file exists. A vertical is complete only when contracts are stable, intended call paths are integrated, bypasses are tested, failure recovery is demonstrated, evidence is reproducible and independent verification accepts the defined operational scope.
