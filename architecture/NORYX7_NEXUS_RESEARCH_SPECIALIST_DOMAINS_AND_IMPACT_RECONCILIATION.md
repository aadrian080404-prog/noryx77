# NORYX7 — NEXUS, Research, Specialist Domains and Impact Architecture Reconciliation

**Review date:** 2026-11-24  
**Source snapshot:** `architecture/system-wide-closure-mirror-world-2026-11-21`, head `a36044b76db9e4a86c3a5a2cc195cde7b46e4a6e` at review start  
**Status:** architecture-only source reconciliation; no runtime changes, integration, test campaign, certification or freeze claimed.

## 1. Purpose and review boundary

This pass continues all twelve workstreams while concentrating on the semantic/evidence path (W06), domain routing and qualification (W10), research egress and source custody (W09/W08), MIRROR WORLD model admission (W07), and community/environmental outcome governance (W12). The findings also constrain identity, runtime, memory, agent, resource and operations workstreams.

The review inspected the current branch versions of:
- `core/universal_intelligence.py`, `core/subtask_uif.py`, `core/subtask_verification.py`;
- `core/verification.py`, `core/reasoning.py`;
- `core/frontier_capabilities.py`, `core/finch.py`, `core/evaluation_campaign.py`;
- `core/` and `ecosystem/` directory inventories;
- `architecture/NORYX7_CROSS_CUTTING_ARCHITECTURE_CONTRACTS.md`, `NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md`, `BUSINESS_PROJECT_FABRIC.md`, and `USER_UNDERSTANDING_FABRIC.md`.

This is a bounded source review, not proof that no implementation exists elsewhere in the full repository, in external providers, or in uninspected subtrees. In particular, a request for a path under `core/` that does not exist is not proof that an equivalent external service cannot exist.

## 2. NEXUS / FRL semantic architecture

### 2.1 Observed substrate

- `core/verification.py` validates TaskSpec well-formedness, supported risk labels, non-null/non-empty output, result identity/cardinality/order, completed status, and a valid VerificationResult marker.
- `core/reasoning.py` creates hypotheses directly from plan-step objectives and checks task identity, non-empty statements and basis references. `InternalSimulator` labels a hypothesis feasible when its statement is non-empty and its task ID matches the task.
- `core/subtask_uif.py` routes bounded subtasks through deterministic keyword/risk routing. The route explicitly carries `route_authority=False`; it changes cognitive routing, not permission.
- `core/subtask_verification.py` checks exact result coverage, identity/order, completed status and the `agent_result` verification marker. Its `SubtaskEvidence` stores output as a string and a boolean verified marker.
- `core/universal_intelligence.py` selects one of a fixed set of domain labels using keyword overlap and deterministic scoring. `assess` validates assessment shape, duplicate domains, strategy labels, supplied evidence strength values, contradiction flags and uncertainty thresholds. Its evidence coverage is an arithmetic mean of supplied strengths.

### 2.2 Semantic limits

These controls are useful structural guards, but they do not independently establish:
- whether a source exists, is authentic, authoritative, current, independent or directly supports a claim;
- whether a cited passage entails the extracted claim, whether units/time/jurisdiction are compatible, or whether evidence is selectively omitted;
- whether an evidence-strength number is calibrated or whether uncertainty is statistically meaningful;
- whether a proof is checked against a named theory/checker, whether a simulation is empirically validated, or whether a claim generalizes out of distribution;
- whether a source-derived output is faithful to the source rather than merely non-empty and correctly associated with a task.

A `verified=True`-like structural marker must never be promoted to semantic truth. The architecture needs typed evidence objects and claim-to-source anchoring before any future FRL/NEXUS result can be admitted for a declared scope.

### 2.3 Required NEXUS claim model

A future canonical claim record should bind:
1. stable claim ID and exact claim text/structured proposition;
2. claim type: observation, source-reported, derived, formal, simulated, forecast, hypothesis, disputed or unknown;
3. source artifact ID, immutable content digest, authenticated locator and capture timestamp;
4. exact source span / media region / table cell / time interval supporting or contradicting the claim;
5. source publisher/author identity where verifiable, source class, jurisdiction and authority scope;
6. extraction method, model/tool version, normalization and transformation lineage;
7. temporal validity, units, coordinate reference and domain schema version;
8. support/contradiction links, independence groups and shared-origin lineage;
9. uncertainty decomposition, missingness and known selection/measurement biases;
10. reviewer identity, review method, decision scope and expiry/revalidation trigger.

Claim admission must preserve dissent and provenance. Repetition, agent consensus, cryptographic signature, confidence score and popularity are not independent truth signals. A signature authenticates an origin/integrity statement only within its key and scope.

## 3. Research acquisition and source custody

### 3.1 Observed behavior

`WebResearchCapability` accepts HTTPS URLs or a configured search URL template, fetches HTML, extracts links, follows up to ten HTTPS links, and returns snippets, status/content-type fields and SHA-256 body digests. The inspected fetch path requires HTTPS and applies timeout/response-size limits.

`ExternalProviderCapability` sends a bounded JSON request to an HTTPS endpoint using an environment-provided bearer token and an execution ID used as an idempotency key. The returned provider payload is parsed by the adapter; a provider-supplied boolean verification field is not a cryptographic receipt.

### 3.2 Missing acquisition controls

HTTPS and a body digest do not by themselves provide safe egress or trustworthy evidence. The architecture must specify:
- canonical hostname allowlists and purpose-specific destination policy;
- DNS resolution and rebinding controls, IPv4/IPv6 private, loopback, link-local and metadata-address denial;
- redirect-by-redirect validation, proxy/environment handling and connection pinning policy;
- response content-type, encoding, decompression and parser isolation;
- per-source rate, byte, time, concurrency and crawl-depth budgets;
- source identity, publisher authority, capture time, retrieval method and immutable content preservation;
- instruction/data separation and prompt-injection isolation for all retrieved text, metadata, HTML and documents;
- robots/licensing/terms and jurisdiction constraints where applicable;
- source deduplication, version history, freshness, retraction and correction handling;
- signed provider receipts binding provider identity, request digest, quote/amount/recipient, response digest, timestamp, expiry and idempotency key.

Research acquisition must not silently turn external content into instructions, trusted memory, executable configuration or authorization policy.

## 4. Specialist routing versus qualified competence

The current UIF is a bounded routing and assessment coordinator, not a registry of qualified specialists. Keyword matching can select a domain label; it cannot prove a model, agent, dataset, tool or reviewer has domain competence.

Every specialist package therefore needs a versioned qualification manifest:
- domain and subdomain scope, jurisdiction, temporal validity and prohibited tasks;
- ontology/schema, units, accepted sources and source exclusions;
- methods, model/dataset/tool versions and known limitations;
- qualification evidence, evaluation population, benchmark lineage and independent assessor;
- calibration status, uncertainty semantics, OOD detection and expiry;
- required second review, professional sign-off and escalation rules;
- liability/ownership, safety constraints, privacy/retention and audit;
- capability bounds, resource budget, fallback and degraded-mode semantics.

A domain label or route is not a capability grant. Domain qualification does not grant action authority. High-risk actions remain behind the canonical identity, policy, authorization and ActionGate path.

## 5. MIRROR WORLD model admission and Reality Bridge

The inspected cognitive simulator is a plan-structure feasibility check. FINCH uses supplied severity, keyword overlap, batch statistics and mean severity by subject. Neither is evidence of calibrated physical, environmental, economic or temporal forecasting.

Each MIRROR WORLD model must declare:
- model class and intended prediction/intervention question;
- governing equations/logic, assumptions, parameter provenance and version;
- spatial/temporal frame, units, boundary/initial conditions and input quality;
- calibration data and fitting procedure, independent validation/holdout set;
- uncertainty, sensitivity, model discrepancy and missing-data treatment;
- validity domain, extrapolation/OOD detection and failure envelope;
- causal versus correlational interpretation;
- benchmark and field-measurement linkage, reproducibility and independent review;
- model-to-reality transfer criteria and explicit non-actuating default.

Reality Bridge must separate scenario recommendation from real-world control. Any actuation requires a separate authenticated device/asset identity, operator scope, safety interlocks, bounded command, human approval where required, precondition check, independent feedback and emergency stop. A visually convincing digital twin is not a calibrated model.

## 6. Environmental and community impact governance

The architecture catalog describes ecology/remediation, agriculture/food systems and community resource systems, while the inspected `ecosystem/` directory contains front/runtime/global-fabric/global-scale/closure components rather than dedicated financial ledger, marketplace, remediation measurement or community-governance engines. This is a bounded directory observation, not a claim about every repository subtree or external service.

The impact system must be outcome-first, not awareness- or activity-count-first.

### 6.1 Project and intervention record

Each project needs:
- community-defined objective, geographic boundary, affected stakeholders and rights-holder consultation;
- baseline period, baseline measurement method, counterfactual and additionality;
- intervention, inputs, labor/time, equipment, funding and supplier provenance;
- output measures (e.g. kilograms collected) kept separate from outcome measures (e.g. verified reduction in leakage/exposure);
- net impact, leakage, rebound, displacement and lifecycle effects;
- uncertainty, confidence interval, measurement error and data gaps;
- independent verifier, sampling method, evidence custody and audit trail;
- safety plan, permits, hazardous-material exclusion and stop-work authority;
- maintenance, durability, reversal risk and post-project monitoring;
- grievance, appeal, correction and adverse-impact remedy.

### 6.2 Funding and contributor boundary

Financial architecture must distinguish donor/contributor funds, project-restricted funds, participant compensation, supplier payments, platform revenue and refundable balances. These require beneficial-owner clarity, segregated accounts/ledger dimensions, double-entry accounting, authorized payment rails, reconciliation, fraud controls, refunds/disputes and independent audit.

Contribution of time must not be misrepresented as a financial investment or guaranteed income. Work assignment requires transparent terms, safety training, insurance/coverage where applicable, safeguarding, fair compensation, grievance and voluntary exit. No one should be pressured into hazardous cleanup or unpaid labor to access essential community services.

### 6.3 Environmental claims

Avoid a single unqualified “impact score”. Report separate dimensions, boundary, baseline, time window, uncertainty and evidence tier. Do not equate money raised, hours volunteered, items collected or modeled carbon estimates with independently verified net environmental benefit.

## 7. Cross-workstream dependency map

| Workstream | Architecture consequence from this pass |
|---|---|
| W01 Identity / authority | Bind evaluator, source reviewer, domain expert, project operator and provider receipt to scoped principals; keep cognitive route separate from authority |
| W02 Runtime / lifecycle | Give acquisition, extraction, assessment, review and admission explicit lifecycle owners and cancellation/timeout semantics |
| W03 Memory / data | Store immutable source artifacts, claim lineage, corrections, expiry and deletion/tombstone behavior without losing audit obligations |
| W04 Agent fabric | Treat specialist roles as qualified manifests; preserve source lineage and dissent across agent collaboration |
| W05 Routing / resources | Budget crawl, parsing, model inference, simulation and independent review separately; no silent fallback that downgrades assurance |
| W06 Evidence / FRL | Canonical claim graph, support/contradiction edges, provenance, semantic entailment and evidence promotion rules |
| W07 MIRROR WORLD | Model manifests, calibration/validation, uncertainty, OOD limits and non-actuating Reality Bridge |
| W08 Surfaces / edge / cloud | Capture consent, source artifact custody and reviewer approvals consistently across browser/mobile/offline surfaces |
| W09 Security / crypto | Safe egress, signed provider receipts, evaluator/source identity, immutable audit and protected evidence storage |
| W10 Specialist domains | Versioned domain manifests, qualification, jurisdiction, expert review and expiry |
| W11 Operations | Source/provider health, evidence pipeline SLOs, incident response, reproducibility and capacity/cost observability |
| W12 Product / community | Segregated funds, contributor safeguards, independent environmental outcome verification and grievance/appeal |

## 8. New architecture decisions proposed (all OPEN)

### ADR-B97 — Canonical Claim and Evidence Lineage
Define claim identity, source-span anchoring, claim types, support/contradiction graph, provenance, temporal validity, uncertainty, independence groups, review and expiry. No truth promotion from repetition, consensus or signature alone.

### ADR-B98 — Research Egress and Content Isolation
Define mandatory destination mediation, DNS/IP/redirect controls, parser isolation, untrusted-content handling, source custody, crawl budgets and provider receipt requirements.

### ADR-B99 — Specialist Qualification and Scope
Define specialist manifests, independent qualification evidence, domain/jurisdiction scope, validity/expiry, calibration, escalation and separation from action authority. This complements existing domain-assurance proposals; it does not replace them.

### ADR-B100 — MIRROR WORLD Model Validity and Reality Transfer
Define model class, assumptions, units, calibration, independent validation, uncertainty, OOD envelope and non-actuating Reality Bridge admission.

### ADR-B101 — Community and Environmental Outcome Accounting
Define intervention baselines, net outcome boundaries, independent measurement, contributor safeguards, restricted funds, ledger separation, grievance and public reporting.

## 9. Closure status and next sequence

All W01–W12 remain **PARTIAL**. This pass adds source-backed architecture detail but does not close any stream.

Next architecture-only work should:
1. map every NEXUS/FRL-like schema and call site across the repository, including external/connector boundaries;
2. reconcile all research acquisition and provider adapters, including gateway and browser ingress;
3. inventory specialist implementations and qualification evidence by subdomain rather than by broad label;
4. complete MIRROR WORLD domain model inventory and environmental/agricultural measurement architecture;
5. trace business/project fund flows and governance requirements to actual source paths or explicitly classify them as planned/external/unknown;
6. reconcile the new ADRs with existing B76, B90–B96 to avoid duplicate or conflicting decisions;
7. only after architecture review, plan integration and comprehensive verification.

No runtime, tests, dependencies, workflow, deployment, frozen baseline or pull-request merge was changed by this document.
