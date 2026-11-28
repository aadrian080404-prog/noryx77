# NORYX7 — Assurance, offline continuity, semantic verification and release-governance reconciliation

**Review date:** 2026-11-23  
**Source baseline:** repository `main`, source inventory carried forward from the 2026-11-22 closure cycle  
**Scope:** architecture-only source reconciliation; no runtime code, tests, dependencies, integration, deployment or frozen baseline changed.

## 1. Executive disposition

This pass deepens W03, W06, W07, W09, W10 and W11 while preserving dependencies on W01/W02/W05/W08/W12. The inspected code contains useful fail-closed primitives, but their assurance levels differ materially:

- local structural checks are not semantic truth verification;
- event buffering is not a durable security operations platform;
- a signed artifact manifest is not a complete software supply-chain attestation;
- an offline encrypted queue is not a durable distributed outbox;
- a monotonic SQLite marker is not a hardware-rooted anti-rollback guarantee;
- a simulation result marked feasible is not a calibrated physical or socio-economic simulation;
- a proposal-only self-improvement pipeline is not an independently governed release process.

These distinctions become explicit architecture requirements and decision records below.

## 2. Security telemetry and operational response — W09/W11

### 2.1 SecurityEventBus

`core/observability.py` provides a bounded, in-memory, append-only list of typed security events. It validates event kind, component, severity and a 64-character lowercase hex evidence digest, and assigns a local sequential event ID and wall-clock timestamp. Capacity exhaustion raises an exception.

It does not itself provide durable storage, cross-process ordering, authenticated producer identity, event signature, trusted time, tamper-evident chaining, tenant partitioning, remote forwarding, retention, alert correlation, incident ownership or response automation. The local sequence resets with process reconstruction. The evidence digest is supplied by the caller and is not independently resolved to an evidence object.

**Architecture contract:** define an event envelope binding event ID, source workload/device, principal/tenant, execution/action/request IDs, policy epoch, event time plus monotonic sequence, evidence references, classification, severity, integrity signature and schema version. Define durable append, acknowledgement, replay, deduplication, partitioning, retention/legal hold, export and deletion policy. Event ingestion must not be able to block or silently lose a critical authorization decision; critical security events need a separately bounded durable path and explicit backpressure/containment behavior.

### 2.2 Detection is not containment

The event bus docstring explicitly leaves containment to consumers. Architecture must therefore name the owners and state machines for alert triage, incident declaration, credential revocation, device isolation, egress restriction, workload draining, evidence preservation, recovery authorization and post-incident review. A severity integer is not an incident policy.

### 2.3 Egress policy

`core/egress.py` maintains an in-memory allowlist keyed by component, host, port and protocol. It canonicalizes IP literals and lowercases DNS names. It is a policy primitive, not proof that every socket, DNS resolution, redirect, proxy, child process, native extension or platform network path is mediated by it. DNS rebinding, resolved-address policy, IPv4/IPv6 dual-stack, CNAME chains, proxy trust, certificate validation, TLS pinning, redirect reauthorization, rule distribution and emergency revocation remain architecture obligations.

**Required boundary:** every network-capable adapter must use a mediated egress provider or an independently enforced OS/container/network policy. Authorization binds the resolved destination and service identity, not only a caller-provided hostname. Redirects and DNS re-resolution require policy re-evaluation. Deny-by-default is meaningful only when bypass paths are inventoried and blocked.

## 3. Supply-chain and release authority — W09/W11/W08

### 3.1 Existing source primitive

`core/supply_chain.py` defines an artifact manifest with component ID, version, SHA-256 digest, raw Ed25519 signer public key and signature. `SupplyChainVerifier` accepts only signer keys present in a locally supplied trusted-key set and can compare the artifact bytes to the declared digest.

This is useful manifest-signature and content-integrity verification. The source does not establish how the trust set is provisioned, protected, rotated, revoked or recovered. The manifest does not itself bind source commit, build workflow identity, builder environment, dependencies, SBOM, build parameters, reproducibility claim, test evidence, approval quorum, target platform, deployment environment, rollback compatibility or release channel. A signer public key embedded in a manifest is data; trust comes from the independent root-of-trust policy.

### 3.2 Canonical release lifecycle

Architecture must define a signed release attestation chain:

1. source repository and immutable commit/tag;
2. dependency lock and SBOM with vulnerability/license disposition;
3. isolated builder identity and build provenance;
4. reproducibility or explicitly documented non-reproducible build evidence;
5. artifact digest and platform/ABI compatibility;
6. security, quality and policy acceptance evidence tied to exact artifacts;
7. independent release signer(s), approval quorum and key custody;
8. staged promotion across development, test, canary and production;
9. health gates, traffic drain, rollback/roll-forward and schema compatibility;
10. decommission, credential revocation and retained audit evidence.

Mobile/browser artifacts, Python gateway, Go service, Rust runtime, model weights/prompts/configuration, plugins and offline snapshots need one artifact catalog and compatible version policy without assuming one deployment unit.

### 3.3 Self-improvement boundary

`core/self_improvement.py` is explicitly proposal-only: OBSERVE → ANALYZE → PROPOSE → SIMULATE → TEST → VERIFY, followed by an `admit_external()` call. The local class checks sequence order but does not implement the external admission authority. Its stage variable is in-memory and does not record evidence, reviewer identity, patch lineage, protected zones or rollback.

Self-improvement must never modify its own trust roots, authorization policy, release signer, audit path or recovery controller. A proposal requires immutable source/patch digest, threat analysis, tests against protected suites, sandbox/holdout evidence, independent human or separately governed approval, signed release provenance, canary and rollback owner. An agent that generated a patch cannot be the sole verifier or release approver.

## 4. Offline continuity, state and recovery — W03/W08/W09

### 4.1 Snapshot trust

`core/offline.py` models offline states, a bounded snapshot, local execution records and an encrypted synchronization queue. Snapshot integrity uses a SHA-256 digest of canonical fields. A digest detects accidental or unauthorized changes only if the expected digest is independently trusted; it is not a signature or MAC. Snapshot fields include principal, policy/artifact/state versions and capabilities, but the source contract needs explicit issuer, signature, key ID, tenant, device binding, policy epoch, revocation freshness and expiry semantics.

Offline authorization cannot safely treat a previously issued capability as permanently valid. Each offline capability needs a bounded offline lease, permitted operation set, risk ceiling, local anti-rollback anchor and a rule for what becomes unavailable when revocation freshness expires.

### 4.2 Queue and reconnect

The `OfflineSyncQueue` stores encrypted envelopes in an in-memory dictionary with local sequence. It deduplicates by execution ID and binds AAD to the execution ID. The queue does not itself survive process loss, provide durable delivery, atomically commit external effects, guarantee cross-device uniqueness or reconcile unknown external outcomes. Reconnection must not blindly replay operations whose external side effect may already have happened.

Define a durable outbox/inbox protocol with unique operation identity, principal/device binding, base-state version, payload digest, policy epoch, signed envelope, server receipt, idempotency key, retry budget, conflict class, quarantine state and explicit terminal outcome. Delivery semantics must be stated (at-least-once with deduplication is generally more honest than an unsupported exactly-once claim). Unknown outcome becomes INDETERMINATE and requires reconciliation, not automatic retry.

### 4.3 Monotonic anchor

`core/offline_anchor.py` persists highest accepted snapshot timestamp/ID in SQLite WAL with synchronous FULL. The source itself warns that production should use protected storage or a hardware-backed monotonic counter/TPM/HSM. Local database rollback, file replacement, host compromise, clock rollback and restore-from-backup remain outside the protection of a plain SQLite record.

Architecture must define the root of trust, hardware capability profiles, fallback assurance levels, anchor migration, backup/restore and disaster recovery. If hardware anchoring is absent, the system must report reduced anti-rollback assurance and constrain offline privileges accordingly.

## 5. Semantic verification, confidence and evidence — W06/W10

### 5.1 Output verification boundary

`core/verification.py` checks task shape/risk labels, result identities/statuses and output presence/non-emptiness. These are important structural checks, but `verify_output` does not establish factual correctness, domain validity, source support, causal validity, safety or user-goal satisfaction. Its success must not be interpreted as truth.

### 5.2 Hypothesis and simulator semantics

`core/reasoning.py` creates hypotheses by mapping plan-step objectives into hypothesis statements. Its `InternalSimulator` determines feasibility from whether the statement is non-empty and belongs to the task. It is a structural preflight, not a domain-calibrated simulation of physics, economics, medicine, engineering or environmental systems.

MIRROR WORLD must distinguish:
- structural plan validation;
- deterministic constraint checking;
- executable sandbox simulation;
- calibrated numerical/physical simulation;
- empirical model validated against held-out observations;
- causal inference with explicit assumptions;
- expert-reviewed domain judgment.

Every result declares method class, assumptions, input dataset/version, model/version, calibration range, uncertainty, validation evidence and out-of-distribution limits. A structural check must never be promoted to a physical or empirical result.

### 5.3 Metacognitive confidence

`core/metacognition.py` performs identity/count/sequence checks and a challenge-verification call. Its confidence value is the proportion of successful boolean checks in the local evidence list. It is a pipeline-consistency score, not a calibrated probability that the final answer is correct. It should be renamed or explicitly typed as a verification coverage/consistency metric in the canonical semantic contract.

### 5.4 Universal Intelligence routing and assessments

`core/universal_intelligence.py` uses deterministic keyword routing with objective weighted above task input, then risk and text length to choose a strategy/budget. This is an interpretable routing heuristic, not proof of specialist competence. Domain assessments accept confidence, uncertainty, evidence strength and contradictions as supplied values; validation checks ranges and structure, not calibration or independent truth.

A specialist registry must include qualification/evidence basis, supported task scope, jurisdiction/version, model/tool provenance, conflicts, benchmark history, failure modes, reviewer and escalation policy. Confidence must have a named semantics and calibration protocol; contradictory or unsupported evidence remains visible and may block commit.

### 5.5 NEXUS / FRL semantic contract

Canonical evidence and reasoning objects must separate:
- claim/proposition;
- source observation;
- derived inference;
- assumption;
- normative rule;
- simulation result;
- expert judgment;
- verification assertion;
- authorization decision;
- execution receipt.

Each object has stable ID, issuer, source lineage, timestamp/sequence, schema and method version, digest/signature, uncertainty, scope, jurisdiction, consent/classification, retention and supersession/deletion status. Semantic equivalence across languages or model providers must be evidenced, not inferred from matching strings or hashes of raw text.

## 6. Domain fabric governance — W10

The inspected Universal Intelligence domain list includes software/architecture engineering, legal intelligence, medical evidence, scientific research, finance/economics and general reasoning. A route name does not provide a complete operational domain fabric.

Every domain needs a manifest with:
- scope, exclusions and jurisdiction;
- authoritative sources and source freshness;
- professional qualification and reviewer requirements;
- evidence grading and accepted methods;
- uncertainty, contradiction and escalation thresholds;
- human approval requirements and prohibited autonomous decisions;
- data classification, consent and retention;
- incident reporting, liability owner and audit policy;
- update cadence, version compatibility and withdrawal procedure.

For health, legal and finance, the platform must distinguish educational information from regulated professional service, avoid diagnosis/representation/investment execution without lawful authority, and route high-impact decisions to qualified human review. Science and engineering need reproducibility, safety constraints and independent validation. Environmental and socio-economic models need local measurements, lifecycle boundaries, uncertainty and distributional-impact analysis.

## 7. Architecture gate and source audit limits — W01/W02/W11

`core/architecture_gate.py` defines 18 canonical planes and requires non-empty textual contract fields, then checks that path-like tokens named in implementation-boundary strings exist in a small set of roots. `core/architecture_registry.py` supplies one definition per plane.

This is a structural completeness gate. It does not inspect whether a named path actually implements the described behavior, whether every caller uses it, whether duplicate authorities exist, whether policy is enforced at all routes, whether external adapters are deployed, or whether acceptance evidence exists. A path can exist and still be a stub, dead code, partial adapter or unused facade.

The architecture freeze gate must be a separate evidence manifest containing:
- every plane and cross-cutting contract owner;
- source paths and exact symbols/call sites;
- all public entrypoints and privileged dispatch paths;
- dependency/call graph and duplicate/competing authorities;
- deployment artifact and environment mapping;
- threat/failure/recovery analysis;
- data lifecycle and retention;
- resource budgets and SLO assumptions;
- source-to-requirement traceability;
- later verification criteria and evidence owner;
- unresolved items classified as blocking or explicitly deferred.

No 100% architecture-closure claim is permitted while any in-scope item is UNKNOWN, merely inferred from path existence, or lacks an accountable owner.

## 8. Cross-workstream decisions added

| ADR | Streams | Decision required |
|---|---|---|
| B70 | W09/W11 | Security event schema, durable audit pipeline, producer authentication and incident/containment ownership |
| B71 | W09/W11/W08 | Enforced egress boundary, DNS/redirect/proxy handling, revocation and bypass-path inventory |
| B72 | W09/W11/W08 | Software/model/firmware release attestation, SBOM, build provenance, signer governance, promotion and rollback |
| B73 | W03/W08/W09 | Offline snapshot signature, trust root, device binding, lease freshness and degraded assurance |
| B74 | W03/W08/W11 | Durable offline outbox/inbox, delivery semantics, idempotency and indeterminate external outcome reconciliation |
| B75 | W06/W07/W10 | Semantic evidence classes and calibrated simulation/verification levels; structural checks cannot claim truth |
| B76 | W06/W10 | Specialist/domain qualification, source standards, jurisdiction, human review and calibration governance |
| B77 | W01/W02/W11 | Evidence-backed architecture freeze manifest distinct from structural path/field completeness gate |
| B78 | W09/W11 | Self-improvement protected zones, independent admission authority, signed release and rollback |

## 9. Updated workstream disposition

- **W03 State & recovery:** offline snapshot, queue and monotonic anchor source semantics mapped; durable cross-device outbox and hardware root remain open.
- **W06 Semantics & evidence:** structural-vs-semantic verification and confidence semantics clarified; canonical NEXUS/FRL evidence schema and calibration remain open.
- **W07 MIRROR WORLD:** structural feasibility simulation distinguished from calibrated domain simulation; world fidelity and Reality Bridge remain open.
- **W09 Security & assurance:** event bus, egress policy, supply-chain verifier and self-improvement source mapped; durable operations, enforcement, trust roots and independent release governance remain open.
- **W10 Domain fabrics:** keyword routing and domain assessment limits recorded; domain manifests and expert governance remain open.
- **W11 Performance & operations:** durable telemetry, SLO, release, queue and capacity evidence requirements expanded; no fleet readiness claim.
- **W01/W02/W04/W05/W08/W12:** no closure status upgrade implied; their authority, runtime, agent, routing, surface and ecosystem decisions remain partial.

## 10. Freeze prerequisites from this pass

Before architecture freeze, the complete package must resolve the above ADRs or explicitly defer them with owner, risk, scope and acceptance criteria. It must preserve a single source of truth for the 18 canonical planes and identify cross-cutting capabilities without creating accidental extra planes. Integration and comprehensive verification remain subsequent phases, not substitutes for unresolved design decisions.
