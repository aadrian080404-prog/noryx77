# NORYX7 — Distributed evidence, memory custody, research and systems reconstruction reconciliation

**Status:** architecture-only source reconciliation; no implementation or verification claim  
**Review branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Reviewed source snapshot:** `4889dd52aa4b7aec737ed4f910f6f77e6e7fa978`  
**Date:** 2026-11-25  
**Disposition:** W01–W12 remain PARTIAL; integration and comprehensive verification remain deferred.

## 1. Purpose and review boundary

This pass deepens the cross-stream inventory rather than adding another top-level feature list. It follows the actual source boundaries for memory, offline synchronization, provider dispatch, model routing, tool invocation, browser isolation, supply-chain verification and event forecasting. It also separates repository capabilities from the architecture still required for NEXUS/FRL, MIRROR WORLD and authorized Systems Reverse Engineering.

Only architecture documentation is changed in this cycle. The reviewed Python files are evidence anchors, not edit targets. No tests were run as part of this documentation pass, no runtime behavior is asserted beyond the inspected source, and no production readiness or architecture freeze is claimed.

## 2. Source anchors and bounded observations

The following blob IDs identify the exact source versions reviewed at the snapshot above.

| Source | Blob | Observed behavior | Boundary / unresolved question |
|---|---|---|---|
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` | Bounded, locked in-process MemoryStore; validates IDs, kinds, importance and optional execution scope; deep-copies values at ingress/egress. | No persistence, replication, tenant namespace, retention scheduler, tombstone propagation or crash recovery in this class. |
| `core/memory_hierarchy.py` | `d908fcb7252e97072501b94dada23ae571807850` | Bounded L0–L5 key/value records and explicit promotion. | The hierarchy is a local dictionary; level names do not prove storage placement, durability, policy-based promotion or replica consistency. |
| `core/secure_memory.py` | `27727ce69802f3ad4f082bf4b9bc4ef013fa7812` | Serializes JSON-compatible MemoryItem records through EncryptedRecordStore and exposes ciphertext snapshots. | Adapter does not itself provide a durable backend, key lifecycle, replication, restore orchestration or retention/deletion proofs. |
| `core/secure_storage.py` | `0fd726f2bad1ff6e133b46c04039ae2c943d350f` | Authenticated encryption boundary binds namespace and record ID as AAD; records remain in a bounded in-memory dictionary. | Ciphertext-only in process memory is not durable encrypted storage. Backend replacement, crash consistency, backup and restore contracts remain open. |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Defines offline state, signed/hashed snapshot metadata, bounded encrypted outbox contracts, policy/verifier interfaces and reconciliation structures. | Queue/inbox/ack durability and conflict policy must be traced through all callers; an encrypted envelope alone does not prove delivery or exactly-once effects. |
| `core/offline_anchor.py` | `a130043ae7dff949b072ae97fd00137d8051d2ea` | SQLite WAL + synchronous FULL monotonic snapshot anchor, with transactional epoch acceptance. | This protects a monotonic anchor, not the entire offline queue, state journal, key store or external-effect reconciliation. Protected storage/TPM/HSM remains deployment-dependent. |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` | Deterministic registration-order capability selection; execute retries by excluding a provider after any exception. | Exceptions do not reveal whether the provider performed a side effect. Failover can duplicate a logical effect without operation idempotency and reconciliation. |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` | ProviderExecutionGateway resolves a provider and dispatches via a newly constructed ExecutionFabric with a supplied authorization callback. | The action ID is derived from principal/provider/capability and is not a durable logical-operation/attempt/effect identity. No common receipt/reconciliation protocol is established here. |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | ResilientProviderExecutor records provider attempts and uses attempt-specific action IDs with bounded failover. | It remains a separate path from ProviderExecutionGateway and ProviderRouter.execute. A caught exception may follow a real external effect; attempt records do not settle effect certainty. |
| `core/tool_protocol.py` | `1c529fbbf5352469be8ab6633edc48113da8a3bf` | ToolRegistry invokes a handler only when an injected authorizer returns exactly True; ToolResult captures a simple success/value/error/provenance tuple. | It is not the same contract as ToolExecutor/ActionGate. ToolResult lacks canonical operation identity, effect certainty, evidence references and reconciliation state. |
| `core/tools.py` | `a5c2797cce7c803abb272bab761b3288ba0f7e72` | ToolExecutor resolves a capability, invokes canonical ActionGate, then validates a VerificationResult. | The verifier validates output under its own contract; this alone does not establish external-effect observation or independent semantic truth. |
| `noryx7_runtime/model_fabric.py` | `abb8bd9bb3217fff967e898afbdc491eb5082f45` | ModelRequest expresses required/preferred capabilities, budgets, fan-out and runtime/execution identity; candidates are ranked deterministically. | Candidate ranking and model-bound provenance are not proof of model independence, calibrated confidence, source-grounded correctness or semantic agreement. |
| `jarvis/memory/store.py` | `85123bbfe425ed21e7cd7d2dd2a55fdbb532a05d` | Separate simple bounded in-memory key/value store. | A further memory implementation exists outside core; canonical ownership, adapter compatibility, migration and lifecycle are unresolved. |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Bounded event graph; relevance uses keyword/severity; anomaly score uses severity deviation; Forecast records likelihood, horizon and evidence IDs. | The numeric likelihood is heuristic, not calibrated probability. Evidence IDs are not by themselves source custody, independence or causal validation. |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Verifies Ed25519 signatures for a trusted signer over component/version/artifact digest and can verify artifact bytes. | Does not alone prove reproducible build, dependency/SBOM completeness, builder identity, approval, staged promotion, rollback or runtime deployment attestation. |
| `ecosystem/browser_isolation.py` | `73f69b55f7bb6335d6e9294c7d48ebac1868991a` | Static source scan rejects selected integration markers in browser source. | Static marker scanning is not process sandboxing, network egress control, origin isolation, permission mediation or runtime containment. |

A path's existence and a positive unit-level primitive are not proof that all constructors, call sites, production compositions or deployments use that primitive.

## 3. Canonical evidence model required by NEXUS / FRL

NEXUS must be the shared semantic and evidence authority across research, agents, memory, tools, audit, simulations and specialist domains. It must not collapse into a search index, agent persona or untyped collection of citations.

The architecture should distinguish at least these object classes:

1. **SourceArtifact** — immutable identity for a captured source: media type, source URI or controlled locator, acquisition time, content digest, capture method, rights/consent basis, jurisdiction, retention class and custody events.
2. **SourceSpan** — exact byte range, page/paragraph, timestamp/frame/sample interval, code symbol/line range or structured-data path within a SourceArtifact.
3. **Claim** — typed proposition with subject/predicate/object or formal expression, scope, temporal validity, units, assumptions and explicit epistemic status.
4. **EvidenceLink** — relation such as supports, contradicts, qualifies, derives-from, reproduces or supersedes; includes the exact SourceSpan, transformation chain and reviewer/validator.
5. **Derivation** — reproducible transformation with tool/model/version, parameters, input digests, output digest, execution identity and deterministic/non-deterministic classification.
6. **ProofArtifact** — formal proposition, proof term/checker identity, checker version, trust root and result. A formal proof must not be conflated with empirical evidence or simulation output.
7. **Observation** — measured event with instrument/source identity, calibration, uncertainty, sampling window, unit, environment and custody.
8. **SimulationResult** — scenario/world/model versions, initial conditions, boundary conditions, solver, seed, numerical settings, fidelity assumptions, output and validation set.
9. **Forecast** — target event/variable, horizon, forecast timestamp, model version, probability distribution or interval, calibration cohort, scoring rule and later outcome linkage.
10. **ReviewDecision** — independent reviewer identity, competence/scope, conflicts, decision, rationale, time and appeal/correction path.

Evidence lifecycle must support proposed → captured → normalized → assessed → corroborated/contested → admitted → superseded/retracted/expired. These are not synonyms for accepted execution, truth or publication. Corrections must append provenance rather than erase historical custody. Retraction must invalidate dependent claims through explicit graph edges.

### Independence and confidence

NEXUS must track common-cause dependence: same publisher, original dataset, upstream article, model family, provider, sensor, collection campaign, transformation code or shared annotator. Five agents repeating one upstream source are not five independent sources. A consensus score must not multiply confidence as if correlated evidence were independent.

Confidence must be typed and calibrated for the relevant task. Distinguish:
- structural validity (schema, signatures, IDs, hashes);
- source authenticity and custody;
- semantic entailment or contradiction;
- empirical measurement quality;
- formal proof checking;
- simulation validation;
- domain-qualified review;
- operational observation of an effect.

No single boolean `verified` should erase these dimensions.

## 4. FRL and research execution contract

FRL (Formal Reasoning Layer) should produce proof-carrying derivations only where a formal system is applicable. Its result must bind proposition, assumptions, axioms/theory version, proof artifact, checker implementation/version and checker output. A proof checker can establish derivability under declared assumptions; it cannot establish that the assumptions describe the physical world.

Research acquisition must separately record:
- request purpose and authorization;
- allowed domains, protocols, ports and address classes;
- redirect policy, DNS/IP resolution and private/link-local address blocking;
- byte, time, depth and concurrency limits;
- robots/terms/rights and data-protection constraints;
- raw response digest and capture time;
- parser/extractor version and extracted span offsets;
- untrusted-content treatment (prompt injection and executable payloads are data, never instructions);
- source reliability and independence group;
- human review requirements for high-impact conclusions.

The inspected browser isolation scanner is a source-code check, not the research network boundary. The research egress policy must be enforced at the transport/runtime boundary and logged as an auditable decision.

## 5. Systems Reverse Engineering — authorized capability tiers

Systems Reverse Engineering is an architecture capability for understanding systems from evidence, not copying proprietary source or bypassing access controls. It must be scoped by an authorization manifest tied to the asset owner, operator, environment, permitted methods and time window.

| Tier | Mode | Permitted evidence and activity | Required guardrails |
|---|---|---|---|
| SRE-0 | Documentation analysis | Public documentation, supplied manuals, schemas and known interface descriptions. | Source licensing/rights, citations, version scope. |
| SRE-1 | Passive observation | User-authorized logs, packet captures, telemetry, binaries or traffic already lawfully acquired. | Data minimization, secrets/PII redaction, chain of custody, no active probing. |
| SRE-2 | Controlled black-box testing | Explicitly authorized test instance; bounded input/output experiments, protocol conformance and differential behavior. | Written scope, rate limits, test accounts, no production impact, stop conditions. |
| SRE-3 | Isolated dynamic analysis | Authorized binaries/devices in disposable sandbox, emulator or lab network. | No uncontrolled egress, snapshot/rollback, malware containment, resource caps, evidence capture. |
| SRE-4 | Source-assisted reconstruction | Source or debug artifacts supplied by rights holder, with dependency and build context. | License/IP constraints, provenance, access control, no redistribution outside grant. |

Every run needs: AssetAuthorizationManifest, scope digest, operator/principal, permitted target identifiers, allowed methods, prohibited actions, start/end, rate/resource bounds, emergency stop, evidence retention, findings classification and signed report. Unknown ownership or ambiguous authorization defaults to passive/public-only analysis. No stealth, credential theft, persistence, destructive action, unauthorized exploitation or evasion is part of this capability.

The existing `core/cyber_range.py` is a synthetic sandbox foundation; it does not establish these tiers or a general reverse-engineering engine. The architecture must define adapters for protocol inference, state-machine reconstruction, binary metadata, dependency mapping, behavioral differential tests and reproducible lab captures, each separately authorized.

## 6. MIRROR WORLD: model and experiment contract

MIRROR WORLD must distinguish the real-world observation layer, the model layer and the simulated counterfactual layer. No simulated state may silently become a real-world fact or trigger a real action.

A WorldManifest should bind:
- domain and geographic/temporal scope;
- source observations and evidence graph version;
- model/kernel identity and version;
- state variables, units, coordinate systems and ontology;
- boundary/initial conditions and assumptions;
- calibration/training data and holdout separation;
- solver, seed, numerical precision and execution environment;
- uncertainty propagation and sensitivity analysis;
- validation metrics, baselines and known failure envelope;
- experiment owner, approval and reproducibility digest.

Domain models must be modular: physical systems, climate/ecology, energy/material flows, logistics, economics, public health, social/community systems and software/cyber environments have different units, causal assumptions, observation error and validation criteria. A common orchestration protocol must not imply one universal model is scientifically valid for all domains.

Calibration and evaluation require temporally and geographically held-out observations, leakage controls, baseline comparison, ablation, sensitivity, uncertainty intervals and post-deployment drift monitoring. For forecasts, evaluate calibration (e.g. reliability and proper scoring rules) separately from discrimination and operational utility. FINCH's severity-derived likelihood is a heuristic signal, not a calibrated forecast probability.

Reality Bridge remains a separate trust zone. A simulation can propose an action; only the canonical authorization, policy, human approval where required, ActionGate and effect-reconciliation path may execute it. A simulation completion flag is never execution authority.

## 7. Cross-stream canonical operation and memory contracts

The provider paths demonstrate why operation identity must be shared. Define one logical Operation envelope with:
- immutable operation_id and idempotency_key;
- parent/child execution lineage;
- principal, tenant, delegated authority and policy epoch;
- target, capability, normalized parameter digest;
- provider/model/tool/device route and route decision;
- attempt_id, dispatch timestamp and transport receipt;
- effect certainty: NOT_DISPATCHED, DISPATCHED_UNKNOWN, OBSERVED_APPLIED, OBSERVED_NOT_APPLIED, PARTIALLY_APPLIED, RECONCILIATION_REQUIRED;
- evidence references for observation and independent verification;
- commit decision and durable journal reference.

An exception after dispatch must transition to DISPATCHED_UNKNOWN unless the adapter can prove no effect occurred. Automatic failover must be blocked or use the same idempotency key with an adapter-specific deduplication contract. A new provider attempt is not a new logical operation. Receipts must identify what the issuer actually observed and be signed by a trusted adapter identity; a result type digest is not an external-effect receipt.

Memory must be divided by lifecycle and authority, not only L0–L5 labels:
- ephemeral working context;
- execution-scoped scratch;
- durable user/tenant memory;
- evidence/source archive;
- event/audit journal;
- model/index/cache;
- offline outbox/inbox;
- recovery checkpoints and tombstones.

Each tier needs owner, backend, encryption/key ID, namespace, replication, consistency, retention, deletion, legal hold, export, recovery point/objective, and conflict resolution. Promotion between tiers must preserve source lineage, consent, classification and deletion obligations. Memory content is not automatically trusted instruction or policy.

## 8. Workstream impact and closure evidence

| Workstream | New reconciliation focus | Closure evidence still required |
|---|---|---|
| W01 Identity | Source, reviewer, adapter, model, tool and operator identities; authority to attest evidence. | Canonical issuer/subject/delegation/revocation map and independent reviewer identity. |
| W02 Runtime | Operation/attempt/effect/commit state machine. | One lifecycle owner, constructor/call-site map and crash/retry reconciliation. |
| W03 Memory | Distinct in-memory, encrypted adapter, SQLite anchor and JARVIS store. | Durable backend contracts, migration, replica/tombstone and recovery proof. |
| W04 Agent Fabric | Agent/model/tool/source lineage and independence. | Qualification registry, delegation attenuation, DAG lineage and result admission. |
| W05 Routing | Provider/model choice separated from node placement and effect certainty. | One route-decision contract, capacity lease and idempotent failover. |
| W06 NEXUS/FRL | Typed claims, exact spans, dependence groups and proof artifacts. | Versioned schemas, checker trust model, source custody and contradiction workflow. |
| W07 MIRROR WORLD | World manifests, calibrated domain kernels and Reality Bridge. | Reproducible experiments, held-out validation and real/simulated state isolation. |
| W08 Interfaces | Browser scanner versus runtime containment; tool and surface receipts. | Origin/egress sandbox, canonical bridge authority and observable effect receipts. |
| W09 Security | Evidence custody, authorization manifests, signing and key lifecycle. | Threat model, key rotation/revocation, egress enforcement and signed adapter attestations. |
| W10 Specialist Domains | Domain-specific model validity and reviewer qualification. | Competency/scope registry, units/standards, calibrated validation and escalation. |
| W11 Operations | Forecast evaluation, model drift, release and incident evidence. | SLOs, independent evaluation, artifact→deployment provenance and rollback drills. |
| W12 Ecosystem | Evidence-backed impact and auditable funds/community operations. | Segregated double-entry ledger, reconciled payments, fraud controls and independent outcome measurement. |

## 9. Explicit unresolved decisions (reuse existing backlog)

This pass does not create a duplicate ADR series. It supplies source evidence and sharpened decision requirements for existing entries:
- ADR-B01–B04: authority, runtime/state and agent lifecycle.
- ADR-B05–B07 and ADR-H01–H03: NEXUS/FRL schema, evidence semantics, wire/version compatibility.
- ADR-H04–H05: MIRROR WORLD model/experiment and Reality Bridge.
- ADR-H07–H10: provider/resource routing, memory lifecycle, key custody and audit/ledger separation.
- ADR-H11–H12: outcome semantics, budgets and scheduling.
- ADR-M02: authorized Systems Reverse Engineering tiers.
- ADR-M03: controlled self-improvement/release lifecycle.
- ADR-M04: domain manifests and qualified review.

All remain OPEN until the architecture decision process records alternatives, owner, rationale, compatibility impact and acceptance criteria.

## 10. Next source-reconciliation pass

Continue all W01–W12 concurrently with the following bounded inventories:
1. Constructor/factory/consumer map for MemoryStore, EncryptedMemoryStore, StateJournal, key providers, ModelFabric, ToolRegistry and device adapters.
2. Full caller graph for ProviderRouter.execute, ProviderExecutionGateway and ResilientProviderExecutor, including nested retries and action identity.
3. Agent parent/child execution lineage, supervisor admission, qualification evidence and concurrency boundaries.
4. NEXUS/FRL schema ownership, exact evidence-span formats, source custody and correction propagation.
5. CyberRange, reverse-engineering inputs, browser and research egress enforcement boundaries.
6. Release artifact→builder→signer→approval→deployment→rollback provenance.
7. W12 payment, escrow, double-entry ledger, marketplace, dispute and independent impact measurement source map.

No workstream closes by document count. W01–W12 remain PARTIAL until the shared architecture is internally consistent, decisions are resolved or explicitly deferred, all constructors and call sites are accounted for, and an approved freeze manifest defines the subsequent integration and verification gates.
