# NORYX7 — Distributed knowledge consistency, contradiction handling and decision reconciliation

**Status:** ARCHITECTURE PROPOSAL — not implemented, not accepted as ADR, not operationally verified  
**Date:** 2026-11-28  
**Scope:** W01–W12, with primary ownership W03/W04/W06/W07/W09/W10/W11/W12  
**Change boundary:** architecture-only. No runtime/source/test/dependency/workflow/deployment or frozen-baseline changes.

## 1. Purpose and governing invariant

NORYX7 must preserve what is known, why it is believed, what contradicts it, who is authorized to decide, and which version of a decision is in force across agents, models, devices, regions, memory tiers and external sources.

**Governing invariant:** agreement, repetition, confidence scores, a digest, a timestamp, a majority vote, or a successful state consensus does not independently establish factual truth. Every admitted claim and decision must retain source lineage, scope, time semantics, uncertainty, contrary evidence, applicable policy and authority.

This architecture separates reality/event occurrence; observation and source testimony; extracted proposition/claim; inference, hypothesis and forecast; policy/rule and normative interpretation; decision/commitment; and replicated state/consensus about that state.

A decision can be procedurally valid while its factual premises remain uncertain. A distributed commit can prove that replicas accepted a state transition; it cannot prove that the proposition encoded in that state is true.

## 2. Bounded source reconciliation

Audited branch snapshot: PR #212 branch HEAD c0656b593b600e63730450609541728d00becfc9. Blob identifiers are recorded below and in the Source Traceability Ledger.

### 2.1 Reasoning and simulation
- core/reasoning.py blob 7bf5d905f07b4805e3505e13408a685d81f7842b: HypothesisEngine.generate() maps each plan step objective to one hypothesis. It does not construct competing causal hypotheses, falsifiable predictions, counterexamples or branch lineage. InternalSimulator.simulate() labels a nonempty statement with matching task ID feasible; this is a structural placeholder, not a domain simulation or empirical test.
- CrossChecker verifies result/hypothesis counts, identities, order, completion and boolean verification markers. It does not establish semantic entailment, source reliability or independent corroboration.

### 2.2 Verification and metacognition
- core/verification.py blob ca80253776bd66a1c0ff4ef32f019c85bf510927: task contract/risk, output presence, result identity/status and state enum checks. It does not itself verify factual truth, source entailment, measurement validity or evaluator independence.
- core/metacognition.py blob 9aed7b2522175f6e4a097631566682cdff6a118f: checks pipeline identities/counts and calls an injected PipelineChallengeVerifier; confidence is the fraction of successful boolean checks. This is a structural pass ratio, not a calibrated probability of correctness. The interface does not itself prove challenge-verifier independence.

### 2.3 Collaboration and evaluation
- core/collaboration.py blob 31e0545a9a6f8f50a09d570d617956cf6cf3572e: Primary → Secondary critique → Primary reconciliation; distinct agent objects/IDs and output digests are checked. The path does not attest distinct model/provider/corpus/prompt/tool/failure domains, source access, or independent qualification. The final output-presence check does not validate factual claims. A REJECT critique is recorded as accepted=false, but reconciliation still proceeds; dissent needs an explicit lifecycle and admission policy.
- core/evaluation.py blob df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e: validates types, ranges and nonempty evidence strings, then aggregates pass flags. It does not authenticate evaluator, case, evidence, execution, holdout isolation or score calibration.
- core/evaluation_campaign.py blob 44db107096abf02f0cde62ba0393f87eda465753: creates deterministic scenarios and a hash-based holdout designation, but does not execute the cases or prevent the caller from recording arbitrary externally produced pass/score/evidence. Holdout designation alone is not holdout secrecy or leakage resistance.

### 2.4 Domain intelligence, forecasting, multimodal and memory
- core/universal_intelligence.py blob 986dd5976b6451a5a75950535c13f4355f57fb0f: keyword-based domain routing; assessments accept caller-supplied evidence strength, confidence and uncertainty. evidence_coverage is a mean of declared strengths, not verified evidence coverage. No qualification issuer or independent specialist credential is bound here.
- core/finch.py blob 4de84c583ba41faa6ff169dd7ed28f2306ed1d09: observations have source/subject/signal/timestamp/severity; graph edges and digest are deterministic local representations. Forecast likelihood is arithmetic mean severity, not empirically calibrated event probability; timestamps lack source clock-quality and valid-time/ingest-time distinction in this module.
- core/multimodal.py blob 8c3fb71a6277806d98c2c294444443ddcc3ff9ee: MediaRef binds modality, content type, digest and locator. Digest binds bytes when created, but the contract does not establish capture authenticity, owner consent, custody chain, source identity, transformation lineage, rights, or claim-level entailment.
- core/memory.py blob 1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd: bounded in-process store, deepcopy isolation and optional execution ID filtering. It does not provide canonical claim/evidence versions, cross-agent provenance, conflict preservation, durable distributed merge or authority-gated promotion.

These are bounded module-level findings at the inspected snapshot; they do not prove absence of external evaluators, source systems, storage, providers or deployment controls.

## 3. Epistemic object model

The canonical model must distinguish the following versioned entities. They are proposed logical contracts, not current code types.

### 3.1 SourceRecord
source_id, issuer/owner, source class, source locator, capture method, acquisition time, source event time, clock quality, jurisdiction, scope, access/consent basis, authenticity evidence, custody events, content digest, transformations, retention and revocation state.

Source classes include primary record, direct observation, instrument measurement, official publication, human testimony, model output, simulation output, derived dataset and policy text. Source class is metadata, not a truth ranking.

### 3.2 Claim
claim_id, canonical proposition, subject/entity references, predicate, object/value, qualifiers, unit, spatial/temporal scope, jurisdiction, modality (asserted/observed/inferred/forecast/normative), polarity, source refs, evidence refs, derivation rule, author/issuer, created/valid/recorded times, confidence model/version, uncertainty, status and supersession links.

A claim is atomic enough to be checked and rebutted. Compound claims must be decomposed where their subclaims can differ in truth, time, jurisdiction or source.

### 3.3 Evidence and derivation
EvidenceRecord binds an immutable source snapshot or measurement to a claim, exact content digest, extraction/normalization transform, locator/page/span/time range, extractor version, custody and verification receipt. DerivationRecord binds premise claim IDs and versions, inference rule/model/tool version, parameters, execution/attempt ID, output claim IDs and verifier receipt.

A content digest proves byte identity under the selected hash assumptions, not origin, truth, consent, completeness or interpretation.

### 3.4 Contradiction and rebuttal
ConflictRecord binds at least two incompatible claims and versions, conflict type, overlapping scope, detected time, evidence, severity, responsible adjudication domain and status. RebuttalRecord binds the challenged claim, counterclaim, counterevidence, falsifier, reviewer identity/qualification and resolution.

Contradictions are first-class records; they must not be deleted or hidden by selecting the latest or most popular statement.

### 3.5 DecisionRecord
decision_id, decision owner/authority, principal, affected scope, objective, claim-set digest and versions, evidence-set digest, policy/rule versions, risk, assumptions, alternatives, dissent, decision rationale, authorization receipt, validity interval, commit sequence, rollback/reopen triggers and review deadline.

A decision's validity is distinct from the truth status of its premises. A decision may be valid under an explicit precautionary policy while the underlying claim remains contested.

## 4. Epistemic state and confidence semantics

Proposed claim statuses:
- PROPOSED — not yet admitted.
- SUPPORTED — evidence meets a named, scoped admission policy.
- REFUTED — sufficient counterevidence under the same scoped policy.
- CONTESTED — material, unresolved conflict exists.
- UNDERDETERMINED — evidence is insufficient to decide.
- STALE — validity/freshness window elapsed or relevant source/policy changed.
- OUT_OF_SCOPE — claim cannot be applied to this entity, time, jurisdiction or decision.
- QUARANTINED — provenance, integrity, safety or source trust is in doubt.
- RETRACTED — issuer/source withdraws the assertion; prior record remains.
- SUPERSEDED — a newer version exists, without implying the old version was false.

Never collapse UNKNOWN, FALSE, NOT OBSERVED, NOT APPLICABLE, NOT YET VERIFIED and NOT AUTHORIZED.

Confidence is not a universal scalar. A confidence value is admissible only with target event/proposition and reference class; method and calibration dataset/version; sample size, uncertainty interval and calibration error; source and evidence coverage; known dependence/common-mode risks; domain and time horizon; evaluator identity and qualification.

Evidence strength, source reliability, model confidence, posterior probability, forecast likelihood and policy assurance are different quantities. Do not average them into one score. The current metacognitive boolean ratio and FINCH mean-severity forecast must not be represented as calibrated confidence/probability.

## 5. Independence graph and multi-agent corroboration

Every evidence/assessment contributor declares a dependency profile: model family/version, provider/serving region, training/data provenance where available, retrieval corpus/indexes, prompt/template/shared context, tools/libraries/browser/source gateways, evaluator identity/owner/conflicts, infrastructure/account/credential/failure domain, transformations and prior agents in the derivation chain.

Represent dependencies as a graph, not a flat list. Two agents are not independent merely because they have distinct IDs or process instances. Shared upstream evidence, model/provider, corpus, prompt or evaluator may create common-mode failure.

Independence levels:
- I0_UNKNOWN — dependency profile unavailable.
- I1_DISTINCT_INSTANCE — separate process/agent identity only.
- I2_DISTINCT_MODEL_OR_PROVIDER — distinct model/provider evidenced, common upstream dependencies may remain.
- I3_DISTINCT_EVIDENCE_PATH — independently acquired evidence/source path and transformations.
- I4_INDEPENDENT_ASSURANCE — separate qualified verifier, controlled holdout/oracle and audited conflict-of-interest/failure-domain controls.

The required level is selected by risk. A hundred agents sharing one model and one source are one correlated evidence cluster for corroboration purposes, not one hundred independent votes. Never infer independence from model brand labels alone.

## 6. Contradiction taxonomy and resolution policy

Conflict classes:
1. Semantic: propositions differ or predicates are interpreted differently.
2. Entity resolution: names/IDs refer to different or ambiguously matched entities.
3. Temporal: valid time, event time, transaction time or clock authority differ.
4. Measurement: units, calibration, instrument, sampling or uncertainty differ.
5. Scope/jurisdiction: different geography, population, contract, law or operating boundary.
6. Provenance: source identity, custody, transformation, signature or integrity mismatch.
7. Version/policy: policy, schema, model, key, revocation or source version mismatch.
8. Causal: competing explanations fit the same observations.
9. Replica/concurrency: two state histories conflict; this is a state consistency problem, not automatically a factual contradiction.
10. Normative: legitimate goals, rights or policy interpretations conflict; factual evidence alone cannot settle values.

Resolution pipeline: preserve both claims and original evidence; normalize only through versioned reversible transforms; align entity/scope/unit/valid-time windows; identify real vs apparent conflict; map common-source dependencies and evidence quality; request targeted primary evidence or a falsifying observation; route to a qualified domain adjudicator; apply explicit policy with dissent and uncertainty; record a signed resolution/decision receipt; reopen on new counterevidence, source revocation, calibration drift or scope change.

No generic last-write-wins, majority vote, confidence averaging or silent overwrite for high-impact claims. If evidence cannot resolve a material contradiction, preserve CONTESTED or UNDERDETERMINED.

## 7. NEXUS / FRL proof and reasoning obligations

Every claim admitted to canonical knowledge must have a typed proof/assurance path: source authenticity and custody; proposition extraction and locator; entity/scope/time normalization; premise and derivation lineage; evidence support and counterevidence search; rule/model/tool version and assumptions; domain validity and uncertainty; independent review level appropriate to risk; reproducible verifier receipt; policy and authority to promote the claim.

Proof obligations differ by claim type:
- factual: source entailment, provenance, scope, contrary evidence;
- measurement: calibration, units, uncertainty, sampling and traceability;
- causal: alternative hypotheses, predictions, intervention/observational limits, falsifiers;
- forecast: reference class, horizon, calibration, drift and proper scoring;
- legal/policy: jurisdiction, effective date, authoritative text, interpretation and qualified review;
- financial: source ledger, double-entry reconciliation, authority and settlement receipt;
- simulation: model validity, parameter provenance, calibration and reality-boundary label.

A symbolic simulator result must be labeled as symbolic. A model-generated explanation is a proposal, not proof. A successful structural verifier is not a semantic oracle.

## 8. Distributed consistency and merge semantics

The temporal consistency architecture remains authoritative for clocks, causal context, aggregate versions and fencing. This document adds epistemic merge rules:

- Claim/evidence records are immutable and append-only; corrections create new versions and explicit supersession/retraction links.
- Claim sets may merge by union only when IDs, canonical encodings, tenant scope and provenance validate; union does not mean all claims are mutually consistent.
- Evidence graphs merge by immutable node identity and lineage; missing parents create an incomplete lineage state, not inferred ancestry.
- Conflicts are materialized deterministically from overlapping proposition/scope/time and versioned conflict rules.
- Decision records are not auto-merged. They require the correct authority, policy version, scope and conflict review.
- Replica consensus establishes which bytes/version are committed, not which claim is true.
- Partitioned nodes may append local observations/proposals with local sequence and bounded authority; they cannot globally promote claims or decisions without required reconciliation.
- Revoked source keys, expired qualifications, superseded policies or invalidated calibrations propagate invalidation to dependent claims and decisions.
- No silent mutation of historical evidence when a source corrects itself; retain the old assertion and append correction provenance.

## 9. Memory admission, retrieval and invalidation

Memory tiers are storage/placement classes, not epistemic trust classes. working/local/edge/cloud/long_term/suspended do not mean verified or authoritative.

Proposed admission stages:
CAPTURED → NORMALIZED → CLAIM_EXTRACTED → PROVENANCE_CHECKED → EVIDENCE_REVIEWED → DOMAIN_ADMITTED → CANONICAL_COMMITTED.

Any stage may route to QUARANTINED, CONTESTED or REJECTED. Only a signed AdmissionReceipt may promote content to canonical shared memory. Agent-local working memory may retain unverified hypotheses only with explicit labels, execution/tenant scope and TTL.

Retrieval returns claim status, source lineage, scope, valid time, confidence semantics, conflict links and policy version alongside the text. If lineage is missing or stale, the answer must expose that condition rather than silently presenting the claim as fact.

Invalidation triggers include source retraction, key revocation, policy epoch change, entity merge/split, instrument recalibration, model/evaluator drift, evidence correction, jurisdiction change and newly discovered counterexample. Invalidation propagates through the derivation graph to dependent claims and decisions.

## 10. Decision and authority separation

The epistemic system may recommend; it does not grant itself authority. Separate claim admission authority; domain qualification authority; policy/rule issuer; decision owner; state commit authority; external legal/financial/physical actuator authority.

For high-impact decisions, require separation of duties and a human or legally competent authority where applicable. A model, agent quorum or consensus protocol cannot manufacture legal consent, payment settlement, medical authority, device ownership or governance mandate.

The DecisionRecord must preserve alternatives and dissent. A decision can be committed only if the caller's authority, scope, current policy epoch, evidence freshness and conflict policy all pass.

## 11. Cross-stream obligations W01–W12

- W01 Identity/trust: bind source issuers, evaluators, specialists and decision owners to identities, scopes, qualification and revocation.
- W02 Runtime/orchestration: make claim extraction, review, challenge, adjudication and commit explicit lifecycle stages with attempt IDs and no hidden promotion.
- W03 Memory/state: immutable claim/evidence graph, bitemporal versions, provenance-aware retrieval, invalidation and conflict-preserving merge.
- W04 Agent Fabric: dependency graph for agents, reviewer independence, dissent, no self-approval and bounded parallel challenge.
- W05 Model/provider/resource: model/provider/corpus dependency disclosure, model version, rate/cost budgets and source-access constraints.
- W06 NEXUS/FRL/evaluation: source entailment, typed proof obligations, alternative hypotheses, falsifiers, holdout isolation, evaluator attestation and calibrated forecasts.
- W07 Mirror World/simulation: separate symbolic, synthetic, calibrated simulation and real-world observation; never promote simulated output as observed fact.
- W08 Surfaces/devices/browser/offline: capture consent, device/source custody, local unverified labels, bounded offline admission and signed reconciliation.
- W09 Security/crypto/audit: canonical signed claim/evidence/decision receipts, tamper-evident audit, key/revocation lifecycle and privacy controls.
- W10 Specialist intelligence: verified domain qualification, jurisdiction, scope, expiry, conflict of interest and adjudication rules.
- W11 Global distribution: deterministic conflict materialization, versioned merge, causal completeness, partition policy and invalidation propagation.
- W12 Economy/governance/impact: financial and impact claims require source ledger, counterfactual, independent audit, authority and immutable correction trail.

## 12. Failure modes and safe behavior

| Failure | Required behavior |
|---|---|
| Source unavailable | Preserve claim as unverified/stale; do not fabricate replacement evidence |
| Two sources disagree | Create ConflictRecord; keep both lineages |
| Same model repeats a claim | Count as correlated support, not independent confirmation |
| Verifier shares generator dependencies | Downgrade independence level; request independent path |
| Missing derivation parent | Mark lineage incomplete; block canonical admission |
| Source key revoked | Quarantine affected evidence and invalidate dependent claims |
| Policy/jurisdiction changed | Re-evaluate scope and effective date |
| Forecast calibration drift | Suspend calibrated probability claim; preserve raw forecast as uncalibrated |
| Replica partition | Preserve local proposals; block global promotion absent authority |
| Human decision conflicts with evidence | Preserve dissent and decision authority; do not rewrite factual claim to match decision |
| Simulation conflicts with reality | Mark model invalid/out-of-calibration and update model provenance |
| New counterexample arrives | Reopen claim/decision and traverse dependent lineage |

## 13. Proposed gap additions

1. GAP-W06-ATOMIC-CLAIM-EVIDENCE-AND-DERIVATION-LINEAGE — canonical claim/evidence/derivation contracts and immutable source locators.
2. GAP-W04-W06-AGENT-DEPENDENCY-GRAPH-AND-INDEPENDENCE-ATTESTATION — evidence dependency graph and defensible reviewer independence levels.
3. GAP-W06-CONTRADICTION-TAXONOMY-AND-ADJUDICATION-LIFECYCLE — typed conflicts, rebuttals, counterevidence, dissent and reopening.
4. GAP-W06-CALIBRATED-CONFIDENCE-AND-FORECAST-VALIDATION — separate confidence semantics, calibration, reference classes and drift.
5. GAP-W03-W06-EPISTEMIC-MEMORY-ADMISSION-AND-INVALIDATION — provenance-gated promotion, retrieval status and dependent-claim invalidation.
6. GAP-W06-W07-SIMULATION-REALITY-BOUNDARY-AND-MODEL-CALIBRATION — distinguish symbolic/synthetic/simulated/observed evidence with calibrated model validity.
7. GAP-W01-W06-W10-SOURCE-EVALUATOR-AND-DECISION-AUTHORITY — issuer, reviewer qualification, jurisdiction, conflicts and decision scope.
8. GAP-W06-W09-SIGNED-CLAIM-EVIDENCE-AND-DECISION-RECEIPTS — canonical signatures, provenance, policy versions and audit binding.
9. GAP-W03-W11-CONFLICT-PRESERVING-DISTRIBUTED-KNOWLEDGE-MERGE — deterministic merge, causal completeness and no silent overwrite.
10. GAP-W06-W12-HIGH-IMPACT-CLAIM-AND-DECISION-ASSURANCE — financial, governance, health, safety and impact assurance with independent authority.

These are proposed closure requirements, not verified implementation defects or accepted decisions.

## 14. Decisions left OPEN

Open: canonical proposition/claim language and ontology governance; source trust classes and jurisdictional authority; confidence/calibration representation; evidence independence attestation availability; conflict severity and adjudicator selection; holdout custody and secrecy; claim retention/privacy/deletion law; immutable evidence storage and encryption; revocation/invalidation propagation guarantees; decision reopening and appeals; NEXUS/FRL proof language and solver boundaries; human review thresholds.

No specific graph database, event broker, proof assistant, ontology or consensus technology is selected by this proposal.

## 15. Acceptance criteria for later integration and verification

1. A claim can be traced to exact source bytes/locator, issuer, capture, transformations and applicable time/scope.
2. Repeating the same source through multiple agents cannot inflate independence.
3. Every reviewer has an auditable dependency profile and required qualification.
4. Contradictory claims coexist and create typed conflicts; no silent last-write-wins.
5. A conflict can be rebutted, adjudicated, appealed and reopened with immutable history.
6. Confidence is never shown without method, reference class, calibration and uncertainty metadata.
7. FINCH forecasts are labeled uncalibrated until validated on temporally separated data with proper scoring and drift monitoring.
8. Metacognitive structural pass ratios are not labeled probability of correctness.
9. A holdout cannot be approved by a caller-supplied evidence string alone; case, execution, evaluator and artifact are cryptographically bound.
10. Simulation, model output, observation and authoritative source are distinguishable in all downstream contracts.
11. Memory cannot promote unverified content to canonical shared state without AdmissionReceipt.
12. Source revocation/correction invalidates dependent claims and decisions within a measurable propagation bound.
13. Replica consensus cannot be interpreted as epistemic truth.
14. High-impact decisions preserve authority, assumptions, dissent, alternatives and rollback/reopen triggers.
15. All W01–W12 integrations expose provenance and epistemic status end-to-end.

**Closure statement:** This document specifies a cross-stream epistemic architecture and records source-bounded gaps. It does not claim that NEXUS/FRL, semantic proof, independent verification, calibrated forecasting, or distributed epistemic memory are operationally complete. W01–W12 remain PARTIAL pending architecture reconciliation, implementation, integration and later evidence-backed validation.
