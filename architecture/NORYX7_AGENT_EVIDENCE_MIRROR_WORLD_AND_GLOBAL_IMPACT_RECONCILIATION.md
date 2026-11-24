# NORYX7 — Agent Execution, Evidence Admission, MIRROR WORLD and Global Impact Reconciliation

**Review date:** 2026-11-24  
**Reviewed branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source snapshot:** `8627284c7a638383706a461745cb18674235b4f7`  
**Mode:** architecture-only, bounded source reconciliation. No runtime, tests, dependencies, workflows, deployment, branch protection or baseline changes.

## 1. Purpose and assurance vocabulary

This pass continues W01–W12 together, concentrating on the hand-off between agent selection, execution, evidence admission, simulation, memory and global/community outcomes.

Every statement is classified as one of:
- **declared architecture** — a contract or design target exists;
- **source behavior** — behavior is visible in the inspected implementation;
- **operational guarantee** — requires deployment, durable state, external enforcement or evidence beyond a local class;
- **verified assurance** — requires a named, reproducible evaluation result and scope.

A source behavior is not automatically an operational guarantee. A boolean named `verified` is not semantic truth. A hash or signature proves only the properties and trust scope of its cryptographic construction.

## 2. Agent fabric: multiple dispatch authorities still coexist

### 2.1 Native AgentCore / AgentFabric

The inspected `core/agent_core.py` defines an explicit phase lifecycle (understanding, planning, authorizing, acting, observing, verifying, reflecting, responding), a bounded step count, an optional authorization hook and a response verification flag. Execution is sequential under one per-agent lock; a failure leaves the agent in FAILED until reset.

`core/agent_fabric.py` binds an AgentCore to an AgentIdentity and registered skill names. It checks the identity registry at registration and dispatch, rejects a mismatched principal already present in request context, invokes an injected principal authorization callback, and then calls the selected agent.

Important limits:
- the principal arrives as a string argument; the fabric itself does not resolve its issuer, tenant, session, device, audience or freshness;
- skill registration verifies only that a name exists in the local registry, not qualification or version validity;
- candidate selection is deterministic sorted order and returns the first authorized available agent; no health/capacity/latency/cost/fairness optimization is visible here;
- callback exceptions fail closed for that candidate, but there is no durable decision receipt in this class.

### 2.2 AgentMesh / AgentCoordinator / OperationalAgentFabric

The repository has several different agent abstractions:
- `core/agent_mesh.py`: role registry and deterministic first matching role; no identity registry or authorization in this class.
- `core/coordination.py`: ActionGate, trusted-agent checks, execution-bound child tasks and result admission; `assign` takes only `plan.steps[:max_agents]`, so it does not represent a complete arbitrary DAG scheduler and may leave additional plan steps outside this assignment pass.
- `AgentCoordinator.verify_consensus`: requires distinct agent IDs and equal outputs, but identity distinctness alone does not prove independent models, data, providers, teams or failure domains.
- `core/operational_fabric.py`: wraps supervisor selection, dispatch and admission for one task; it does not itself define durable distributed leases, cancellation propagation, retry semantics or cross-node recovery.
- `core/agent_runtime.py`: local heartbeat/status registry using the injected clock; it is not distributed liveness or remote health attestation.

### 2.3 Required canonical dispatch contract

Before integration, define one lifecycle owner and explicit adapters for legacy fabrics. The canonical record must bind:
1. intent/request/task/subtask/step/execution/attempt/dispatch IDs without conflation;
2. authenticated principal, tenant, issuer, session, device/workload identity and policy epoch;
3. agent identity, version, skill manifest and qualification scope;
4. assignment reason, eligible candidates, capacity reservation and lease;
5. authorization decision, capability, target, risk, policy version and expiry;
6. DAG dependencies, concurrency, ordering, cancellation and deadline;
7. dispatch acknowledgement and side-effect certainty;
8. result provenance, verification scope and independent admission;
9. retries, idempotency, compensation and terminal state;
10. durable audit correlation and recovery owner.

Agent routing must remain cognitive allocation, not authorization. No agent, skill, role, consensus or supervisor may create authority by selection alone.

## 3. Evidence admission: structure versus semantic support

### 3.1 Current source behavior

- `core/verification.py` checks task contracts, risk labels, output presence, result identity/cardinality/order, completion and a valid verification marker. Its generic `verify_output` rejects null/empty strings or bytes; it does not determine whether a claim is true or supported.
- `core/reasoning.py` derives hypotheses directly from plan-step objectives. The internal simulator checks that the hypothesis is non-empty and tied to the same task ID; this is structural feasibility, not a domain simulator.
- `core/subtask_uif.py` routes subtasks to a specialist label and explicitly sets `route_authority=False`.
- `core/subtask_verification.py` enforces exact subtask result coverage/order and an `agent_result` verification marker, then sets `commit_eligible`. Its `SubtaskEvidence` stores output as a string and a boolean verified marker; this is not claim-to-source semantic entailment.
- `core/universal_intelligence.py` defines evidence/assessment records with source labels, claims, numeric strength, confidence, uncertainty and contradiction strings. Shape and range checks do not independently authenticate the source or calibrate those values.
- `core/evaluation_campaign.py` generates deterministic local adversarial cases and a seeded holdout selection, and approves only when every required evaluation dimension is present and passing. It does not itself create independent evaluation evidence or establish a production test pass.

### 3.2 Canonical evidence model still required

A result intended to influence trusted decisions must carry:
- exact claim/proposition and claim type (observation, reported, derived, formal, simulated, forecast, hypothesis, disputed, unknown);
- immutable source artifact digest, source identity/class, capture time and authenticated locator;
- exact supporting/contradicting span, table cell, media region or time interval;
- extraction/transformation/model/tool versions and full lineage;
- jurisdiction, units, schema and temporal validity;
- support/contradiction graph and shared-origin/independence groups;
- uncertainty decomposition, missingness, bias and out-of-domain warnings;
- reviewer identity, review method, approval scope, expiry and revalidation trigger.

Consensus, repeated citations, agent count, popularity, confidence scores and cryptographic signatures must not be treated as independent truth signals.

## 4. MIRROR WORLD: model admission and reality transfer

The MIRROR WORLD architecture already describes world graphs, immutable scenario snapshots, experiment manifests, domain-specific simulation kernels, synthetic browser worlds, cyber ranges and a Reality Bridge. The key architectural risk is treating a model that runs deterministically as a model that predicts reality.

Every model package needs a manifest containing:
- domain, question, model class and intended decision scope;
- equations/rules, assumptions, parameter provenance and version;
- units, coordinate/time frame, boundary and initial conditions;
- calibration data, fitting method, independent validation and holdout provenance;
- numerical stability, convergence, precision and deterministic/stochastic mode;
- sensitivity, uncertainty, model discrepancy and missing-data handling;
- validity envelope, OOD detection, extrapolation and known failure regions;
- benchmark-to-field evidence, reproducibility and independent reviewer;
- prohibited uses, safety case, expiry and rollback/supersession state.

The Reality Bridge is non-actuating by default. Any real-world action must cross a separate authenticated asset/device identity, scoped operator authorization, precondition checks, safety interlocks, bounded command, independent feedback, audit receipt and emergency stop. A simulation result is not an authorization token.

## 5. FINCH and temporal forecasts

`core/finch.py` provides bounded event observations, relationship graph snapshots, relevance/anomaly records and forecast-shaped outputs. These structures are useful for event fusion, but a forecast record containing a likelihood, horizon and evidence IDs does not establish calibrated probability or predictive validity.

Required forecast qualification:
- target event definition and base rate;
- forecast issuance timestamp and fixed horizon;
- observation cutoff and leakage prevention;
- calibration dataset and time-split/rolling-origin evaluation;
- proper scoring rules, calibration curve and uncertainty intervals;
- baseline comparisons and ablation;
- missingness, drift, intervention and distribution-shift handling;
- false-positive/false-negative cost and decision threshold ownership;
- independent holdout, model version and reproducible campaign manifest.

FINCH must report “unqualified hypothesis” until the relevant forecast package passes a declared evaluation scope. It must not be used for covert identification, surveillance or high-impact decisions without separate lawful basis, consent and human governance.

## 6. Global memory and cross-front consistency

`ecosystem/global_fabric.py` defines L0–L5 levels and a `MemoryRecord` with record ID, version, payload digest, replica labels and provenance digest. The inspected `GlobalMemoryFabric` stores only these metadata records in a bounded in-process dictionary; the payload is hashed, not retained by this object. `require_redundancy` counts supplied replica labels, but does not contact or verify distinct healthy durable replicas.

The adjacent identity-authorization structure records identity/session/device labels, role, capabilities and policy/authorization digests. It is a local index, not an issuer, revocation authority, tenant boundary or cross-region consensus service.

The canonical memory contract must cover:
- owner tenant/principal and access-control policy;
- source, purpose, consent receipt and data classification;
- content digest, encrypted payload reference and key version;
- schema, lineage, derived-data relationships and provenance;
- retention/expiry, legal hold, correction and deletion tombstone;
- replica identity, health, failure domain, durability and digest agreement;
- consistency level, stale-read policy, conflict resolution and anti-rollback;
- offline synchronization and deletion propagation to backups/caches/derived artifacts.

L0–L5 are storage/latency tiers, not permission tiers. A replica label is not proof of redundancy.

## 7. W12 ecosystem: product architecture versus accountable operations

The inspected business/project and community architecture specifies a lifecycle from opportunity/feasibility through execution, verification, delivery, accounting and audit. The product architecture also distinguishes customer funds, third-party funds, company revenue and project funds. These are requirements, not evidence that a regulated payment rail, double-entry ledger, settlement reconciliation, marketplace dispute process or community governance engine is deployed.

Canonical financial/project boundaries must distinguish:
1. user-owned balances and user-authorized transactions;
2. third-party/merchant/customer funds;
3. company operating revenue and commissions;
4. restricted community/project contributions;
5. grants/donations with purpose restrictions;
6. participant compensation, refunds, chargebacks, fees and taxes.

A model/agent may calculate or propose a transaction, never directly move funds. Money movement requires an authorized provider, explicit consent, beneficiary/purpose validation, limits, idempotency, double-entry entries, settlement receipts, reconciliation, dispute/refund path and independent audit.

Community project governance must include membership and decision rights, transparent budgets, quorum/appeal, conflict-of-interest declarations, safeguarding, worker safety, fair compensation, voluntary exit, grievance/remedy and anti-capture protections. Time and expertise contributions must not be misrepresented as investments or guaranteed income.

Environmental impact must distinguish activity from outcome:
- collected kilograms versus verified material recovered;
- planted trees versus survival/additionality;
- modeled emissions avoided versus measured net lifecycle effect;
- money raised/hours volunteered versus independent ecological or health outcomes.

Each intervention requires a baseline, boundary, counterfactual, time horizon, leakage/rebound/displacement accounting, uncertainty, independent measurement and post-project durability monitoring. Do not collapse incompatible effects into one unqualified score.

## 8. Parallel workstream delta

| Workstream | Additional finding in this pass | Required architecture closure | Status |
|---|---|---|---|
| W01 Identity | Agent dispatch accepts principal labels and local identity registry state | Issuer/tenant/session/device binding, policy freshness and signed dispatch receipts | PARTIAL |
| W02 Runtime | Multiple dispatch abstractions; no single durable lifecycle owner demonstrated | Canonical DAG/attempt/lease/cancel/retry/effect lifecycle | PARTIAL |
| W03 Memory | Global fabric stores metadata/digests and replica labels, not payload durability | Ownership, consent, payload custody, consistency and deletion propagation | PARTIAL |
| W04 Agent fabric | AgentCore, AgentFabric, AgentMesh, Coordinator and OperationalFabric overlap | One authoritative dispatch owner and compatibility adapters | PARTIAL |
| W05 Routing | Sorted first-match and bounded truncation are not global scheduling/capacity semantics | Capacity-aware placement, fairness, backpressure and complete DAG coverage | PARTIAL |
| W06 Evidence | Output-presence and verification markers are not semantic evidence admission | Claim-source entailment, lineage, uncertainty and independent review | PARTIAL |
| W07 MIRROR WORLD | World/scenario architecture exists; model-to-reality validity needs scoped evidence | Model manifests, calibration, validation, OOD and non-actuating Reality Bridge | PARTIAL |
| W08 Surfaces | Front/device sources do not establish one lifecycle or shared durable receipts | Cross-surface principal, consent, idempotency and evidence custody | PARTIAL |
| W09 Security | Authority, evidence custody and provider receipts need a common trust chain | Signed grants/receipts, key lifecycle, egress and immutable audit | PARTIAL |
| W10 Domains | Specialist labels and evidence strengths do not qualify expertise | Versioned qualification, jurisdiction, calibration, reviewer and expiry | PARTIAL |
| W11 Operations | Local registries/campaign objects do not establish distributed health or campaign execution | Durable telemetry, service ownership, reproducible campaigns, DR and release evidence | PARTIAL |
| W12 Ecosystem | Business/community/impact capabilities remain architecture requirements | Segregated funds, ledger, governance, safeguards and independent outcome accounting | PARTIAL |

## 9. Existing decision mapping — no duplicate ADRs

This pass creates no new ADR series. Reconcile the findings with:
- B79/B80/B85–B88: canonical principal, IDs, dispatch ownership, DAG, consensus independence and result admission;
- B70/B77/B89/B97: durable audit, evidence-backed freeze, structural-vs-evidence distinction and claim lineage;
- B81/B103: global memory custody, isolation, deletion and context semantics;
- B83/B84/B101: funds segregation, community governance and environmental outcome accounting;
- B90/B91/B92: assurance ladder, evaluation campaign integrity and FINCH temporal qualification;
- B93/B100: MIRROR WORLD graph/model validity and Reality Bridge;
- B95/B96/B98: global fabric adapters, provider attestation, research egress and content isolation;
- B99: specialist qualification and scope;
- B104: durable dispatch/outbox and uncertain side-effect reconciliation.

Where earlier ADRs overlap, consolidate rather than create parallel authorities. All listed decisions remain OPEN/PROPOSED unless separately accepted through the architecture decision process.

## 10. Closure status

W01–W12 remain PARTIAL. This pass adds source-grounded architecture requirements; it does not implement integration, distributed persistence, semantic truth checking, calibrated forecasts, model validation, financial rails, community governance or production operations. No tests or CI results are claimed by this document.
