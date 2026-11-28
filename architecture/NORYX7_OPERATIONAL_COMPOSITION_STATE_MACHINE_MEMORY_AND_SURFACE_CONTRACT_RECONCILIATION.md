# NORYX7 — Operational Composition, State Machine, Memory and Surface Contract Reconciliation

**Review date:** 2026-11-25  
**Source snapshot:** `0cf3ace262d362454e0537b239c920613f885cd3`  
**Mode:** architecture-only, source-anchored reconciliation across W01–W12  
**Change boundary:** no runtime, test, dependency, workflow, configuration, deployment or frozen-baseline changes

## 1. Executive result

This pass reconciles four contract families that must agree before the architecture can be frozen:

1. ingress and principal/session normalization;
2. operation, execution, dispatch and external-effect lifecycle;
3. memory/evidence custody and durable state;
4. resource, agent, model and surface placement.

The repository contains useful implementations in each family, but the same logical task can cross components whose identifiers, lifecycle vocabularies, persistence scopes and trust assumptions differ. The required next step is a contract-level convergence map, not a wholesale rewrite.

W01–W12 remain PARTIAL. Existing ADR-001 through ADR-005 and the H/M decision series remain open unless their own acceptance evidence is met.

## 2. Exact source anchors inspected

| Path | Blob SHA | Observed behavior | Boundary not established |
|---|---|---|---|
| `web/app.py` | `a03d012d6f9f2fdbfb8a5e64397511e5ac692360` | FastAPI exposes session/execute gateway routes and a separate direct `/api/chat` runtime path; runtime/gateway are process-cached. | All routes share authentication, principal mapping, durable state and one deployment-wide composition. |
| `gateway/server.py` | `b434cdbe118ecea48029adcd2c954fa1ac14461c` | Gateway session issue/verification and RuntimeAdapter delegation. | All ingress routes traverse it. |
| `gateway/runtime_adapter.py` | `6661fbc150c77ba79d3b1f16cc0f66742b20f935` | Converts authenticated request to TaskSpec and checks HYPERSYNTH result before response. | Parity with direct chat, CLI, JARVIS, mobile and other surfaces. |
| `core/actions.py` | `5e2fc212abea2873bb471b12e6fe6f5021664e97` | Exact-action, execution/principal/key-fingerprint-bound one-shot grants and ActionGate primitives. | Durable/distributed nonce use, issuer identity lifecycle and uniform adoption by every executor. |
| `core/identity.py` | `e6e8e5b03135251baca489643f86c7d81a755a08` | Ed25519 agent identities and a locked local identity registry with revoke/trust checks. | Cross-process revocation freshness, tenant principal mapping or external workload/device identity. |
| `core/coordination.py` | `c5743872a5b50765db04e4a42739e9ad238ad983` | AgentCoordinator assigns at most max_agents plan steps, creates a fresh execution ID and executes assigned agents sequentially. | Full DAG admission, caller execution identity continuity, concurrency, leases and semantic consensus. |
| `core/agent_mesh.py` | `25c9162750708e53742862f9f413fdf5200ca08f` | AgentMesh role-matches and selects the alphabetically first candidate. | Qualification, trust freshness, capacity, locality or independence. |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` | Bounded action engine with optional adapter, signer, identity registry, journal, authorization and replay controls. | All production facades instantiate and use the same engine and mandatory trust profile. |
| `noryx7_runtime/contracts.py` | `9bb6632b214e8d9d3221c9ccf03ab6233209a184` | Execution status currently has CREATED/RUNNING/SUCCEEDED/REJECTED/FAILED/CANCELLED. | Explicit partial, indeterminate external-effect and compensation states. |
| `noryx7_runtime/scheduler.py` | `5d87d38e17c93dd26975119bb3af1dddd6c132b9` | Validates DAG dependencies and emits deterministic topological order. | Parallel execution, resource leases, cancellation/join, fairness or partial-result semantics. |
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` | Bounded in-process MemoryStore with deep-copy isolation and optional execution filter. | Durable persistence, tenant/principal ACL, retention, source provenance, replication or backup. |
| `jarvis/memory/store.py` | `85123bbfe425ed21e7cd7d2dd2a55fdbb532a05d` | Separate simple in-process key/value store. | Deep-copy isolation, execution/tenant scope, encryption, expiry, deletion propagation or common core-memory semantics. |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` | MediaRef carries modality, content type, digest and locator. | Capture authenticity, rights, consent, custody, transformation lineage or claim entailment. |
| `core/resource_router.py` | `4f7bf28200edd05f1236d9779437e4aa43bba8ab` | Deterministic device/edge/cloud tier selection from complexity/privacy/latency flags. | Live capacity, jurisdiction, network quality, cost, queue depth, attested placement or failover lease. |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite WAL/FULL append-only verified-state commits with digest and schema version. | Deployment configuration, protected filesystem, cross-journal saga or remote effect reconciliation. |
| `core/offline_anchor.py` | `a130043ae7dff949b072ae97fd00137d8051d2ea` | SQLite monotonic snapshot anchor with rollback checks. | Hardware-backed anti-rollback and durable offline outbox/inbox/acknowledgement. |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Bounded observation graph, heuristic relevance/anomaly and forecast primitives. | Calibrated probability, causal inference, source independence or field validity. |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Trusted-key Ed25519 manifest and artifact-byte digest verification. | Trusted builder, dependency/SBOM provenance, approval quorum, deployment measurement or rollback. |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` | Typed cross-front receipt with intent/source/target/execution/principal and evidence digest. | Signer identity, durable storage, observed external effect or verified final commit. |

These are source-level observations at the stated ref. A constructor or class being present does not prove universal caller adoption.

## 3. W01/W02/W08 — ingress and principal contract

### 3.1 Route convergence

The inspected FastAPI app has two distinct request paths:

- `POST /v1/session` and `POST /v1/execute` go through NoryxGateway and RuntimeAdapter.
- `POST /api/chat` directly builds a TaskSpec and calls OperationalNORYXRuntime.

The source does not show the direct chat route invoking SessionAuthority. This is a route divergence requiring an explicit trust decision; it is not, by itself, proof of an exploitable public endpoint because reverse-proxy or upstream controls are outside the inspected source.

**Normative requirement:** every ingress adapter must produce the same authenticated RequestContext contract before cognition or privileged execution. The contract should bind:

- immutable request and operation IDs;
- verified principal subject, tenant, issuer and authentication assurance;
- session/device/workload identity and audience;
- policy/revocation epoch and freshness;
- source surface, channel authentication and trusted-hop chain;
- user intent, data classification, consent/purpose and deadline;
- idempotency key and trace correlation.

Untrusted request metadata may request an identity but cannot assert one. A trusted upstream identity requires explicit proxy trust, header-stripping, channel authentication and replay rules.

### 3.2 Authority separation

Keep these distinct, linked by explicit adapters:

- user/tenant principal assertion;
- agent cryptographic identity;
- device/workload identity;
- session authentication;
- capability/authorization grant;
- execution identity.

A client ID, agent ID, execution ID or device ID must never be silently cast into another identity class. Session authentication permits a request to enter the system; it does not grant arbitrary tool or provider capability.

## 4. W02/W03/W05/W08/W09 — canonical operation and effect lifecycle

### 4.1 Identifier hierarchy

Define one logical operation envelope with separately typed identifiers:

| Identifier | Scope | Invariant |
|---|---|---|
| request_id | user/surface submission | stable across ingress retries of the same request |
| operation_id | one logical requested outcome | stable across provider/agent retries and recovery |
| execution_id | one orchestrated attempt lifecycle | created once by the coordinator and propagated to all children |
| plan_id / plan_version | one accepted plan revision | immutable once execution begins |
| step_id | one node in a plan DAG | stable within plan version |
| action_id | one authorized side-effect intent | exact target and parameters bound |
| attempt_id | one dispatch attempt | unique; never reused as operation identity |
| provider_operation_id | target's operation handle | recorded when remote target supplies one |
| journal_sequence | durable event order | scoped to journal identity and schema epoch |

Existing types use overlapping subsets of these fields. A compatibility adapter must explicitly map them; no field should be overloaded to stand for another.

### 4.2 Canonical effect states

Use a two-axis model: orchestration status and effect certainty.

**Orchestration:** PROPOSED → VALIDATED → PLANNED → AUTHORIZED → RUNNING → RESULT_ADMITTED → COMMITTED, with REJECTED/CANCELLED/FAILED/PARTIAL as terminal or resumable outcomes according to policy.

**Effect certainty:** NOT_DISPATCHED → DISPATCH_INTENT_DURABLE → DISPATCHED_OR_POSSIBLE → EFFECT_CONFIRMED / EFFECT_REJECTED / EFFECT_INDETERMINATE → RECONCILED.

A timeout after bytes may have left the process is not equivalent to a pre-dispatch validation error. A local exception after a remote commit cannot be reported as “no effect”.

Retry eligibility is computed from capability class, provider guarantees, durable idempotency key, target status lookup and current effect certainty. When a target cannot answer whether an effect happened, privileged retry is blocked or sent to an explicit manual/compensation workflow.

### 4.3 Receipt vocabulary

Do not conflate:

- intent accepted;
- authorization granted;
- dispatch attempted;
- target acknowledged;
- payload returned;
- output digest calculated;
- executor attested;
- result independently verified;
- external effect observed;
- state durably committed.

Every receipt states which one it proves, who issued it, which operation/attempt it binds, how it is authenticated, and its evidence retention scope.

## 5. W03/W06/W09/W10/W12 — memory, evidence and deletion custody

### 5.1 Separate memory semantics

The core MemoryStore and JARVIS MemoryStore are not interchangeable. The first deep-copies MemoryItem objects and can filter by execution ID; the second is a simple mutable key/value map. Both are process-local.

Architecture must distinguish:
- ephemeral working context;
- durable user memory;
- agent/skill memory;
- source/evidence artifacts;
- domain records;
- security audit;
- financial/community ledger.

A storage adapter cannot silently merge these namespaces. Every read/write requires tenant/principal scope, purpose, consent/legal basis, retention, classification, encryption/key version, source lineage, policy version and audit identity.

### 5.2 Retrieval completeness

Context hydration returns a typed result: COMPLETE, EMPTY, PARTIAL, STALE, DENIED or UNAVAILABLE. Failure to read memory must never silently become an apparently complete empty context.

Cross-execution memory access requires an explicit sharing grant. L0–L5 are placement/retention tiers, not authorization, durability or consistency guarantees.

### 5.3 NEXUS evidence object

The canonical evidence model must bind:

- immutable SourceArtifact ID, source URI/provider, publisher/issuer and acquisition time;
- exact SourceSpan (page, byte/character range, timestamp or media segment);
- content digest, signature/transport evidence and custody chain;
- language, extraction/OCR/transcription method and transformation lineage;
- rights/consent, purpose and retention;
- Claim ID/type, temporal scope, jurisdiction and confidence semantics;
- support/contradiction/qualification edges with exact spans;
- source independence/common-cause group;
- reviewer/evaluator identity, method and policy version;
- correction, retraction, expiry and supersession events.

A content hash proves byte identity relative to the hashed content; it does not prove publisher authority, truth, rights or claim entailment. A MediaRef locator and digest are likewise not full capture provenance.

### 5.4 Separate ledgers

Security audit, evidence/provenance, domain state and financial/community accounting remain distinct stores with explicit correlation IDs. W12 payments, escrow, marketplace settlement and environmental impact cannot be inferred from an agent action receipt or a generic audit event.

## 6. W04/W05/W06/W10 — agent assignment and result admission

The current AgentCoordinator source truncates assignment to the first `max_agents` plan steps and creates a new execution ID inside execute(). The scheduler provides topological ordering but executes are not thereby concurrent. AgentMesh selects by role and alphabetical ID.

Required contract:

1. Preserve the complete plan DAG; never silently truncate.
2. Distinguish queued, blocked, ready, leased, running, completed, partial, failed and cancelled nodes.
3. Keep one coordinator-issued execution ID across parent, child, tool, provider, evidence and state records.
4. Assign agents using qualification, declared skills, current trust, health, capacity, jurisdiction, privacy, cost and independence constraints.
5. Issue a bounded, attenuated delegation lease bound to principal, task, agent, resource, policy epoch and expiry.
6. Support cancellation, lease expiry/fencing, result join, partial failure and dissent retention.
7. Admit output only after task/step identity, schema, provenance, evidence and policy requirements are checked.
8. Model Primary/Secondary independence explicitly: separate agent IDs do not establish independent model/provider/context/source/failure domains.

Plan cardinality, agent count, concurrency, action budget, token budget and physical resource capacity are independent dimensions.

## 7. W05/W07/W08/W11 — placement and resource lifecycle

The current ResourceRouter is a deterministic heuristic. It is useful as a policy baseline, but it cannot be treated as live resource scheduling.

A placement request must include data classification/residency, jurisdiction, capability, latency deadline, cost ceiling, capacity, trust/attestation, network policy, failure domain, energy/carbon objective and user consent. Placement returns a signed, expiring lease with owner, reservation, fencing token, quotas and cancellation semantics.

Device, edge and cloud are separate trust and failure domains. Offline execution is not an automatic cloud fallback; reconnect requires snapshot freshness, revocation checks, replay-safe outbox/inbox, conflict policy and explicit uncertain-effect reconciliation.

MIRROR WORLD simulation and FINCH forecasts must label model version, data/source cohort, assumptions, fidelity tier, calibration, holdout, uncertainty and OOD state. Simulated outcomes, forecasts, observations and formal proofs remain distinct artifact types.

## 8. W09/W11 — release, keys and operations

A signed artifact manifest is one link, not an entire software supply-chain proof. The release chain must bind source commit, dependency lock/SBOM, builder identity and environment, build provenance, artifact digest, signer key version, approval quorum, vulnerability policy, deployment identity/measurement, staged promotion, rollback and incident response.

Operational requirements include:
- a named composition profile per deployment;
- mandatory versus optional constructor dependencies;
- secret/key source, rotation and revocation;
- journal path, encryption, filesystem protection, backup and restore;
- process/replica topology and shared state guarantees;
- network egress enforcement at the actual socket boundary;
- SLOs for availability, latency, cost, recovery time and data loss;
- telemetry/audit retention and privacy policy.

## 9. W10/W12 — domain and public-impact qualification

Each domain adapter needs a versioned qualification manifest: jurisdiction, permitted purpose, operator/specialist qualifications, source classes, review requirements, calibrated limits, prohibited actions, escalation and expiry. Domain outputs must state whether they are informational, decision support or execution-authorized.

Environmental/community impact must bind baseline, counterfactual, geography, time window, measurement method, independent verifier, uncertainty, duplicate prevention and grievance/correction path. Financial contributions, restricted funds, expenses, compensation and impact outcomes require segregated double-entry accounting and independent reconciliation. A projected impact or community participation count is not an independently verified outcome.

## 10. Existing operational notes: historical evidence, not current status

`NORYX7_OPERATIONS/00_CURRENT_STATE.md` is dated 2026-09-08 and names an earlier branch and test baseline. `01_INTEGRATION_CONTRACTS.md` and `02_OPERATIONAL_RUNTIME.md` preserve useful historical contracts and test claims, but this review did not rerun those tests or verify the described environment at the current source snapshot.

Therefore:
- preserve these notes as historical continuity material;
- do not quote their test totals as current CI status;
- do not infer present deployment health or provider availability from them;
- refresh them only during the later controlled integration/verification phase.

## 11. W01–W12 closure dependencies

| Stream | Contract decisions that must be frozen | Acceptance evidence later required |
|---|---|---|
| W01 | principal assertion, issuer/consumer roles, delegation, revocation freshness | cross-process identity/revocation and negative authorization tests |
| W02 | one coordinator lifecycle, operation IDs, facade ownership, typed outcomes | constructor/call-site trace and end-to-end lifecycle |
| W03 | journal namespaces, state/effect saga, durable memory, backup/deletion | crash/restart, corruption, restore, replication and deletion tests |
| W04 | registry, qualification, delegation leases, DAG and result admission | multi-agent adversarial/partial-failure and independence evidence |
| W05 | provider idempotency, retry owner, resource lease and budget | ambiguous timeout, duplicate suppression, capacity/fencing tests |
| W06 | NEXUS evidence/claim schema and semantic verification | source-span entailment, contradiction, evaluator independence and calibration |
| W07 | simulation fidelity, model/data manifest, Reality Bridge | holdout, OOD, field calibration and isolation evidence |
| W08 | ingress/surface parity, browser/device sandbox, offline sync | route matrix, platform isolation and reconnect/replay tests |
| W09 | KMS/HSM, egress, audit, supply-chain and release lifecycle | key rotation/revocation, network bypass, builder/deployment provenance |
| W10 | specialist/domain qualification and jurisdiction | independent domain review and measured error/uncertainty |
| W11 | SLOs, capacity, cost/energy, incident and DR | load/failure/restore/latency/cost evidence |
| W12 | payment/ledger custody, governance, impact measurement | reconciliation, dispute, independent impact verification |

## 12. Next parallel work

- **W01/W08:** complete every ingress route and trusted-hop matrix; resolve direct chat route semantics.
- **W02/W03:** define coordinator-issued operation IDs, lifecycle/effect dual state machine and cross-journal saga.
- **W03/W06/W12:** freeze separate data custody classes, evidence lineage, retention/deletion and financial ledger boundaries.
- **W04/W05:** complete full DAG assignment, leases, provider idempotency and common-cause independence.
- **W06/W07/W10:** finish typed epistemic artifacts, simulation fidelity and domain qualification manifests.
- **W08/W09/W11:** define device/browser isolation, socket-level egress, release attestation and operational SLO/DR.
- **Cross-cutting:** map every contract to one owner, source path, version, caller, error state and later acceptance test.

## 13. Disposition

This document refines existing ADRs and gap IDs; it creates no duplicate decision series and accepts no ADR. It does not authorize code changes, integration, comprehensive tests, merge, deployment or architecture freeze. All W01–W12 remain PARTIAL.
