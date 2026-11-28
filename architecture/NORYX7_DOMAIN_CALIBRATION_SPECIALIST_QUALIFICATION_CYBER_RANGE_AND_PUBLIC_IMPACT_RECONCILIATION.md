# NORYX7 — Domain Calibration, Specialist Qualification, Cyber-Range Assurance and Public-Impact Accounting Reconciliation

**Review date:** 2026-11-24  
**Reviewed source ref:** `81d6688804ed56ac3e8b55f5d1e8eff97e0fe8e7`  
**Scope:** architecture-only reconciliation across W06, W07, W09, W10, W11 and W12, with dependencies into W01–W05 and W08. No runtime, test, dependency, workflow or deployment changes.

## 1. Executive result

NORYX7 has useful bounded primitives for event analysis, specialist routing, agent critique, evaluation aggregation and synthetic cyber simulation. The key unresolved boundary is the difference between a well-formed model output and a calibrated, independently supported, domain-qualified, operationally safe conclusion.

This review separates five kinds of claims that must never be conflated:
1. a deterministic score or heuristic;
2. a model-generated assessment;
3. an empirically calibrated forecast;
4. a formal proof relative to explicit assumptions;
5. a real-world outcome established by independent measurement.

## 2. Source-backed findings

### 2.1 Universal Intelligence and specialist routing — W04/W06/W10

Inspected `core/universal_intelligence.py`, `core/agent_skills.py`, `core/collaboration.py`.

- `UniversalIntelligenceFabric` currently has six explicit domain keyword maps (software, architecture, legal, medical, science, finance) plus general reasoning. The architecture domain catalog in `NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md` defines thirteen domain packages. This is a catalog-to-router coverage gap, not evidence that all domain implementations are absent.
- Routing is deterministic keyword scoring over task objective/context. It is a bounded routing heuristic, not semantic domain recognition or proof that an assigned specialist is qualified.
- `DomainAssessment` accepts free-form domain/conclusion/evidence/source/strength/confidence/uncertainty fields. Well-formed numeric ranges do not establish source authenticity, calibration, reviewer independence, domain competence or jurisdictional validity.
- `assess` calculates evidence coverage as the arithmetic mean of caller-supplied evidence strength values. It sets verification validity from absence of contradiction and uncertainty <= 0.5; commit eligibility additionally checks high risk. These fields are structural assessment outputs, not a qualified expert sign-off or empirical truth verdict.
- `AgentSkillRegistry` records a skill name, description, handler and risk class. Its default handler returns `None`; registration does not establish competence, tested performance, license, jurisdiction, expiry or authorization.
- `AgentCollaboration` performs a Primary → Secondary critique → Primary reconciliation sequence and requires distinct agent objects/IDs. The evidence digests are SHA-256 digests of generated output strings, not source evidence. Distinct agent IDs do not prove distinct model/provider/data/failure domains. The final verifier's output-presence/contract check does not establish factual entailment.

Architecture requirements:
- specialist manifest: stable identity, domain and subdomain, competence evidence, evaluation record, jurisdiction, scope, permitted/prohibited decisions, source policy, calibration record, reviewer identity, expiry, suspension, appeal and conflict-of-interest declarations;
- distinguish route candidate, qualified specialist, authorized actor and accountable human professional;
- separate cognitive strategy/budget from authority and execution permission;
- evidence objects must bind claim IDs to source URI/artifact, exact span/page/timecode, source version, acquisition time, authenticity status, transformation lineage, independence group and reviewer;
- collaboration independence must be evaluated across model family/version, provider, source corpus, retrieval path, prompt/template, toolchain, operators and failure domain;
- if independence cannot be established, label the result as critique diversity, not independent corroboration.

### 2.2 FINCH event fusion and forecast calibration — W06/W07/W10/W11

Inspected `core/finch.py`.

- `rank_relevance` combines input severity and keyword matches using fixed weights; this is a deterministic ranking score.
- `detect_anomalies` compares severity values against the mean and standard deviation of the supplied batch; it has no domain-specific baseline, seasonality, missingness model, drift test or false-positive calibration.
- `forecast` sets `likelihood` to the arithmetic mean of input severity for each subject. That value is not a probability of a future event. The supplied horizon is metadata; the formula does not model time-to-event or temporal transitions.
- Forecast evidence lists up to four observation IDs but does not carry the source artifact, exact source spans, observation freshness, label outcome or adjudication.
- `EventGraph` creates a deterministic graph digest, but the digest alone does not prove observation truth, temporal completeness, source integrity or causal relationship.

Required forecast lifecycle:
1. define event/target and prediction unit;
2. define forecast horizon and observation cutoff;
3. record immutable feature/label dataset versions and source lineage;
4. split train/validation/test by time and entity/group to prevent leakage;
5. freeze model, features, parameters and baseline before holdout;
6. compare with simple baselines and domain expert judgment;
7. score with appropriate proper scoring rules and calibration diagnostics;
8. report confidence intervals, class prevalence, coverage, false-positive/negative costs and subgroup performance;
9. monitor drift and calibration decay;
10. expire, recalibrate or withdraw forecasts when conditions change.

Forecast fields must be typed as `heuristic_score`, `rank`, `probability`, `interval` or `scenario`. A heuristic score must never be serialized as probability.

### 2.3 Evaluation matrix and evidence admission — W06/W07/W11

Inspected `core/evaluation.py`, `core/evaluation_campaign.py`, `core/verification.py`.

- `EvaluationMatrix` aggregates `EvaluationResult` records and returns true when the list is nonempty and all caller-supplied pass flags are true. It does not enforce assessor independence, evidence artifact existence, campaign identity, coverage completeness or reproducibility.
- Each result's evidence is a non-empty string, not a typed source/evidence reference.
- `VerificationEngine.verify_output` verifies non-null/non-empty output. `verify_agent_results` checks task/agent/execution identity, status and nested validity marker, then output presence. These are important structural contracts but not semantic claim verification.
- Campaign manifests and deterministic cases do not themselves prove that a campaign was run against the exact release, that holdout data remained isolated or that results were independently adjudicated.

Required assurance record:
- campaign ID, exact source commit, artifact/model/policy manifests, environment and dependency digests;
- evaluator identity/authority, independence declaration and conflict check;
- dataset lineage, split manifest, leakage controls and holdout custody;
- test inventory, executed test IDs, logs, raw results, failure classification and reproducibility instructions;
- thresholds fixed before execution, exceptions, waivers and approval chain;
- signed report bound to the tested artifact digest;
- separate states NOT_RUN, RUNNING, PASS, FAIL, BLOCKED, INCOMPLETE, INVALIDATED and EXPIRED.

### 2.4 Cyber-range and authorized systems understanding — W08/W09/W10/W11

Inspected `core/cyber_range.py`.

- The CyberRange is deliberately restricted to synthetic targets in the sandbox trust zone and symbolic techniques; it does not dispatch arbitrary network code. This is a useful safety boundary.
- `OwnerAuthorization` binds principal ID, authorization ID and expiry only. The local `valid_for` check does not bind a specific target, operation set, environment, test window, issuer, revocation state or single-use nonce.
- `SimulationReport.verified` is returned as `True` for the generated symbolic action list; it means the simulator completed this bounded path, not that an exploit hypothesis was independently validated or a real target was safe.
- The report records simulated actions but has no immutable acquisition chain, tool/model versions, test-case oracle, independent assessor or remediation verification.

Required architecture:
- signed authorization manifest binding issuer, owner, principal, exact asset IDs, ownership proof, allowed methods, excluded techniques, data boundaries, time window, rate/impact limits, emergency stop, revocation and audit;
- strict separation of passive observation, synthetic simulation, explicitly authorized bounded validation and production remediation;
- no production probing unless the relevant authorization and safety policy are independently verified at the enforcement boundary;
- preserve raw evidence, hashes, tool versions, timestamps, environment and chain of custody;
- distinguish SIMULATED, OBSERVED, REPRODUCED, VALIDATED and REMEDIATED; no automatic promotion between them;
- remediation closure requires a new test and independent evidence, not a status flag.

### 2.5 Public-interest, financial and environmental outcomes — W12

Inspected `architecture/BUSINESS_PROJECT_FABRIC.md` and `architecture/NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md`.

Existing architecture correctly separates customer funds, third-party funds and company revenue; it disallows hidden commissions and model-initiated transfers. The public-interest domain calls for voluntary contributions, community-defined goals and transparent allocation.

The remaining gap is an outcome accounting and governance contract that links every contribution, expenditure and claimed impact to independently reviewable evidence.

Required W12 architecture:
- separate ledgers for donor/contributor funds, operating funds, restricted grants, customer money, refunds, reserves and company revenue;
- double-entry journal with immutable transaction IDs, currency, counterparty, purpose restriction, approvals, receipt, reconciliation and dispute state;
- no pooling or commingling by default; escrow/custody/payment provider responsibilities explicit;
- conflicts of interest, related-party transactions, procurement thresholds, dual control, whistleblower protections and independent audit;
- public allocation rules, beneficiary privacy, opt-in consent, appeal and grievance channels;
- environmental impact record with baseline, counterfactual, additionality, boundary, leakage, rebound, permanence, uncertainty, measurement method, sampling, independent verifier and expiry;
- distinguish money raised, money spent, activity delivered, output measured, outcome estimated and impact independently verified;
- no claim of carbon reduction, pollution removal, biodiversity gain or health benefit based only on participant counts, model estimates or self-reported activity;
- publish negative results and uncertainty as well as successful outcomes.

## 3. Canonical specialist and evidence lifecycle

`DOMAIN_REQUESTED → ROUTE_CANDIDATE → QUALIFICATION_CHECKED → SCOPE_AUTHORIZED → SOURCES_ACQUIRED → CLAIMS_ANCHORED → ASSESSMENT_PRODUCED → INDEPENDENCE_REVIEWED → DOMAIN_VALIDATED → HUMAN_ESCALATION_IF_REQUIRED → ADMITTED_FOR_EXPLICIT_SCOPE → EXPIRED_OR_REVOKED`.

No single boolean `verified`, `commit_eligible` or `passed` field can replace the typed evidence record and its authority.

## 4. Cross-workstream dependency map

| Contract | Owners | Consumers |
|---|---|---|
| Specialist identity, competence, scope and expiry | W01/W10 | W04/W06/W07/W12 |
| Source-anchored claim and evidence lineage | W03/W06/W09 | W04/W07/W08/W10/W12 |
| Forecast target, temporal dataset and calibration | W06/W07/W10 | W04/W05/W11/W12 |
| Evaluation campaign and assessor independence | W06/W09/W11 | W02/W04/W07/W08/W10 |
| Cyber authorization and custody | W01/W08/W09 | W06/W10/W11 |
| Simulation/observation/validation state semantics | W06/W07/W09/W10 | W04/W08/W11/W12 |
| Funds segregation and double-entry accounting | W01/W09/W11/W12 | W06/W10 |
| Environmental baseline and independent measurement | W06/W07/W10/W12 | W05/W11 |
| Human escalation and appeal | W01/W10/W12 | W04/W06/W07/W08 |

## 5. Existing ADR consolidation

Retain existing decision authorities; do not create a duplicate ADR series.

| Existing ADR | Reconciliation | Status |
|---|---|---|
| B76/B99 | Specialist qualification, competence, jurisdiction, conflicts, expiry and suspension | OPEN |
| B88/B90/B97 | Source-anchored claims, independence groups and semantic admission | OPEN |
| B91 | Campaign execution, holdout custody and assessor independence | OPEN |
| B92/B93/B100 | FINCH/MIRROR WORLD calibration, temporal holdout, drift and model validity | OPEN |
| B94 | Cyber/media observation custody and transformation lineage | OPEN |
| B71/B96/B98 | Authorized cyber acquisition scope and enforcement boundaries | OPEN |
| B83/B84/B101 | Funds segregation, double-entry accounting, community governance and impact verification | OPEN |
| B105/B106 | Do not duplicate; any new lifecycle detail must be merged into the existing canonical decisions after owner review | REVIEW |

## 6. W01–W12 impact

- W01: bind specialist and verifier identities to issuers, scope and revocation.
- W02: carry assessment, campaign and real-world outcome states through durable operation lifecycle.
- W03: preserve evidence artifacts and transformations with access, consent, retention and tombstones.
- W04: schedule by qualification and task scope, not role/skill labels alone.
- W05: include data locality, cost, energy and capacity in experiment and impact placement.
- W06: anchor every claim, evaluation and corroboration to inspectable evidence.
- W07: calibrate physical, ecological, economic and event forecasts against independent observations.
- W08: distinguish synthetic/simulated/observed device and browser evidence.
- W09: authorize acquisition, protect custody and attest the tested artifact.
- W10: maintain specialist qualification, conflict and escalation controls.
- W11: retain exact campaign/release evidence, drift, incidents and audit records.
- W12: reconcile funds and independently measure community/environmental outcomes.

All W01–W12 remain **PARTIAL**. This is source reconciliation and architecture specification only; no specialist service, calibrated forecasting system, independent evaluator, cyber validation program, payment service or environmental measurement program is claimed implemented.

## 7. Next architecture-only work

1. Trace specialist manifests and qualification data from registry to scheduler and ActionGate.
2. Define evidence reference schema and claim anchoring shared by NEXUS/FRL, FINCH, collaboration, cyber range and domain packages.
3. Specify forecast dataset lineage, time-based evaluation and calibration artifacts.
4. Reconcile campaign reports with release attestations and exact artifact digests.
5. Define cyber authorization manifest and custody state machine for each permitted acquisition mode.
6. Define W12 accounting journal, governance roles, independent verifier and impact protocol.
7. Cross-check every item against B71–B104 before declaring architectural closure.
