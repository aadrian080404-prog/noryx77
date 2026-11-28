# NORYX7 — Branching Cognition, Evidence Admission, Model Calibration and MIRROR WORLD Reconciliation

**Audit date:** 2026-11-27  
**Audited source-tree HEAD:** `d3630a9857b81801585144ea5fb58cbb416249c1`  
**Scope:** W01–W12; HYPERSYNTH planning/reasoning/execution, agent collaboration, NEXUS/FRL evidence, evaluation/holdout, specialist routing, FINCH forecasting, MIRROR WORLD, cyber-range, multimodal custody, authorized systems reconstruction, global execution and W12 impact.  
**Disposition:** architecture-only source audit and proposed closure contracts. No runtime/source implementation, tests, dependencies, workflows, deployment or frozen baseline changed.

## 1. Executive result

NORYX7 has a substantive bounded cognitive pipeline and a separate architecture specification for a much broader experimental world. The inspected implementation already performs task validation, specialist routing, decomposition, context construction, plan verification, hypothesis generation, an internal feasibility pass, agent allocation, sequential execution, result cross-checking and metacognitive reflection.

The remaining gap is not simply “add more agents” or “make it parallel”. It is to represent and verify the complete lifecycle of alternative explanations, evidence, model assumptions, experiments, falsification, execution dependencies and measured outcomes.

This audit identifies nine new closure gaps. They are architecture requirements from bounded source inspection, not claims that no external implementation exists and not confirmed vulnerabilities.

## 2. Source anchors

| Source | Blob SHA | Observed scope |
|---|---|---|
| `core/hypersynth.py` | `187699d6e0945a2b1e8a9b194cd9001b1af8cd9f` | Bounded cognitive phases, planner limits, one hypothesis/simulation stage per plan step, assignment loop and action gate |
| `core/reasoning.py` | `7bf5d905f07b4805e3505e13408a685d81f7842b` | Hypothesis derived from plan objective; internal simulator checks task/statement presence and structural IDs |
| `core/metacognition.py` | `9aed7b2522175f6e4a097631566682cdff6a118f` | Pipeline consistency checks, challenge-verifier seam and reflection confidence |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` | Task/result contract and identity checks; output verification checks presence |
| `core/collaboration.py` | `31e0545a9a6f8f50a09d570d617956cf6cf3572e` | Sequential Primary → Secondary critique → Primary reconciliation; output digests |
| `core/evaluation.py` | `df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e` | Evaluation result aggregation and all-records-pass decision |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` | Deterministic case/holdout manifest generation; externally supplied results recorded |
| `core/adversarial.py` | `e23813c99f2d7c5b3f6b39f75571d83d4ec101f9` | Deterministic synthetic scenario generation; no scenario execution or external target contact |
| `core/universal_intelligence.py` | `986dd5976b6451a5a75950535c13f4355f57fb0f` | Bounded keyword specialist routing and caller-supplied assessment/evidence-strength fields |
| `core/agent_skills.py` | `281d294ee0142a8dd33db5d61f634f95943db231` | Declarative skill registration; registration not qualification or permission |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Heuristic relevance/anomaly scoring, arithmetic mean severity forecast, temporal event graph digest |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` | Synthetic sandbox targets and symbolic attack phases |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` | Modality, content type, SHA-256 digest and locator envelope |
| `architecture/NORYX7_MIRROR_WORLD_ARCHITECTURE.md` | `61d53f8a47dd5b03e5988fc8f7888d6f337dc993` | Full architecture specification for worlds, models, experiments, kernels, measurement and Reality Bridge; explicitly no simulator implementation claimed |
| `architecture/NORYX7_CROSS_CUTTING_ARCHITECTURE_CONTRACTS.md` | `3f24597d0f37f2b8e0424376f9eb810874c74a61` | NEXUS/FRL, research acquisition, multimodal, systems understanding, improvement and governance contracts |

## 3. Source-backed findings

### 3.1 HYPERSYNTH performs bounded orchestration, not yet general branching cognition

The inspected `HypothesisEngine.generate` creates one hypothesis per plan step. Each hypothesis statement is the step objective and its basis is the step ID. It does not generate multiple competing causal explanations for a single observation, preserve parent/child branch lineage, specify predicted observations or falsifiers, or manage branch pruning/reopening.

The `InternalSimulator` currently marks a hypothesis feasible when its statement is non-empty and its task ID matches. It does not evaluate domain equations, constraints, causal consequences, numerical stability, empirical calibration or counterexamples. Its verification confirms internal result structure and feasibility flags, not whether the simulated world is a faithful model.

The HYPERSYNTH path bounds planner steps by `min(max_steps, max_agents)`, rejects plans longer than `max_agents`, allocates agents over plan steps and executes assignments in a sequential loop. Round-robin agent selection is not parallel execution. Agent capacity, plan-step count, branch count, DAG width and worker concurrency are different budgets and must be modeled separately.

**Architecture requirement:** add a versioned HypothesisBranch graph with explicit alternatives, parentage, assumptions, evidence links, predicted observables, falsification criteria, uncertainty, resource cost and lifecycle. Preserve rejected and contradicted branches. Separate exploratory branches from executable plan DAGs. Add a scheduler contract for dependency-ready work, bounded concurrency, fairness, cancellation, retry policy and operation/effect reconciliation.

### 3.2 Metacognition and verification enforce structure, not factual truth

The verification engine checks task shape and, for generic output, non-null/non-empty presence. HYPERSYNTH CrossChecker and metacognitive reflection validate result counts, task/step identity, execution identity, completion status and verification markers. These are useful fail-closed structural controls; they do not establish semantic entailment, source authenticity, external factual correctness or domain-valid inference.

Metacognition's challenge-verifier interface provides a useful seam, but the presence of a separate verifier object does not by itself prove independence. Independence must be evaluated across model/provider, version, prompt/template, retrieval corpus, evidence sources, toolchain, operators and failure domain.

**Architecture requirement:** define ResultAdmissionReceipt tied to the exact output digest, claims, evidence, verifier profile/build, method, scope, policy epoch and limitations. Distinguish structural validity, semantic consistency, formal proof, empirical validation and operational outcome.

### 3.3 Agent collaboration is a useful critique protocol, not independent corroboration

`AgentCollaboration` runs a Primary proposal, a Secondary critique and a Primary reconciliation in sequence. It requires different agent objects and IDs, and records SHA-256 digests of the generated text. This establishes a bounded critique handshake. It does not prove different model families, providers, retrieval data, prompts, tools or operational failure domains. The digests identify output bytes; they do not authenticate source evidence or independently verify claims.

**Architecture requirement:** attach an IndependenceProfile to each participant and EvidenceLineage to each claim. If independence cannot be established, label the result “diverse critique” rather than “independent corroboration”. A critic must be able to reject, request evidence, identify contradiction and return indeterminate without the primary agent's reconciliation erasing the dissent.

### 3.4 Evaluation campaign manifests do not establish executed holdout evaluation

`EvaluationCampaign` deterministically generates adversarial cases and identifies holdout indices from a seed/hash rule. The campaign module explicitly says it generates cases only and does not execute them. `scenario(index)` can return a generated case; `record` accepts externally supplied pass, score and evidence fields. `EvaluationMatrix` validates field types/ranges and aggregates them; it does not authenticate evaluator identity, bind evidence to a case execution, enforce holdout access separation or prove that holdout labels were not used during development.

The all-dimensions-present gate is a useful completeness check, but it is not an independent evaluation campaign receipt.

**Architecture requirement:** immutable EvaluationProtocol, sealed DatasetManifest, role-separated training/validation/holdout access, CaseExecutionReceipt, evaluator attestation, artifact-under-test digest, environment manifest, raw outcome reference, adjudication and leakage audit. A holdout must not be accessible to the component being tuned. Repeated tuning against the same holdout must invalidate its status as an untouched final test set.

### 3.5 Specialist routing is not specialist qualification

`UniversalIntelligenceFabric` routes using bounded keyword maps. Its Evidence and DomainAssessment fields accept free-form source/claim and caller-supplied strength/confidence/uncertainty. Numeric range validation does not establish calibration or truth. `AgentSkillRegistry` stores names, descriptions and handlers; a declarative skill or default no-op handler is not evidence of demonstrated competence.

**Architecture requirement:** SpecialistQualificationManifest must bind person/agent identity, domain/subdomain, benchmark record, competence evidence, jurisdiction, permitted scope, expiry/revocation, conflicts, reviewer and accountable human where legally or professionally required. Route selection, qualification, authorization and accountability remain separate decisions.

### 3.6 FINCH produces heuristic scores, not calibrated forecasts

The current relevance score combines severity and keyword matches. Anomaly scoring compares severity within the supplied batch. Forecast likelihood is the arithmetic mean of severity values grouped by subject; the horizon is metadata rather than a temporal event model. The graph digest canonicalizes nodes/edges but does not prove source authenticity or causal relation.

**Architecture requirement:** define forecast target, prediction unit, horizon, cutoff, base rate, feature lineage, training period, calibration set, drift policy and outcome adjudication. Evaluate with proper scoring rules (e.g. Brier/log loss), reliability diagrams, calibration error and domain-appropriate baselines. Forecasts without calibration must be labeled heuristic scores, not probabilities.

### 3.7 MIRROR WORLD architecture is broad, but implementation and validation remain separate

The MIRROR WORLD specification already describes reality-source gateway, provenance registry, world models, scenario graphs, immutable experiment specs, orchestration, domain kernels, event/state ledger, measurement, calibration, evidence admission and isolated Reality Bridge. It explicitly says no simulator/runtime implementation is claimed.

This specification must be reconciled against actual domain-kernel inventory and evidence. A model marked calibrated or validated must identify its exact domain, geography, temporal horizon, resolution, operating regime, calibration dataset, holdout dataset, known failure regions and validation protocol. A digital twin cannot be “validated” globally based on a narrow test. Model agreement is not independent real-world truth.

**Architecture requirement:** ModelValidityProfile and CalibrationReceipt per model/kernel; immutable WorldSnapshot and ExperimentManifest; reproducible seed/environment; uncertainty propagation; sensitivity analysis; out-of-distribution detection; independent measurement comparison; model drift and retirement. Simulation output remains synthetic/model-derived until a separate RealityObservationReceipt supports an empirical claim.

### 3.8 Cyber-range and systems reconstruction must preserve scope boundaries

The inspected CyberRange accepts only synthetic targets in the sandbox trust zone and produces symbolic actions. It does not demonstrate live target reverse engineering. The cross-cutting architecture already defines authorized systems understanding: exact asset ownership/authorization, passive observation versus active probing versus exploit simulation, no unauthorized credential/private-data extraction, no proprietary-code copying, and reproducible findings scoped to tested versions.

**Architecture requirement:** SystemScopeAuthorization with target owner, asset identifiers, allowed techniques, rate/budget limits, time window, data handling and stop conditions. Each inferred protocol/state machine/dependency must link to captures, exact observations, parser/tool version, coverage and uncertainty. Separate passive trace analysis, active measurement and sandbox emulation; never treat synthetic CyberRange evidence as proof of a live system weakness.

### 3.9 Multimodal digest is not media custody

`MediaRef` binds modality, content type, digest and locator. This is a useful reference envelope, but it does not encode original capture device, source principal, consent/purpose, acquisition time quality, transformations, derived transcript/OCR alignment, retention/rights, calibration or chain of custody.

**Architecture requirement:** MediaCustodyRecord with original payload digest, capture/source identity, device attestation, acquisition time, consent/purpose, license/rights, transformations and tool versions, coordinate/time alignment, derived artifact lineage, retention and deletion obligations. Preserve original and derived representations as separate evidence objects.

## 4. Cross-stream architecture consequences

- **W01:** principal, specialist qualification, evaluator identity, owner authorization and human accountability are distinct assertions.
- **W02:** branch exploration, plan DAG, execution operation and external effect require distinct IDs and lifecycles.
- **W03:** branch histories, evidence, model snapshots, experiment manifests and evaluation receipts need durable versioned custody and recovery.
- **W04:** agents produce proposals and critiques; agent count is not independent evidence.
- **W05:** branch and simulation scheduling require explicit resource reservations and concurrency budgets, not only a maximum agent count.
- **W06:** NEXUS claims bind to exact source spans and transformations; FRL proofs bind to exact propositions/theories/checkers; empirical and formal results remain distinct.
- **W07:** MIRROR WORLD needs scoped model validity, calibration, uncertainty and a Reality Bridge separate from simulation.
- **W08:** browser, sensor, audio, video and document acquisition need media custody and explicit source provenance.
- **W09:** verifier, model, dataset and experiment artifacts require signed provenance and reproducible build/version references.
- **W10:** specialist routes require qualification and domain calibration; skill registration alone is insufficient.
- **W11:** distributed experiment workers require fenced leases, immutable snapshots, deterministic replay and durable result collection.
- **W12:** environmental/social/economic interventions require counterfactual baselines, measurement protocols, independent observations and anti-double-counting; simulation estimates must not be reported as realized impact.

## 5. Proposed shared contracts (architecture proposal, not accepted ADR)

- `HypothesisBranch`: branch ID, parent ID, task/goal, proposition, assumptions, evidence refs, predicted observations, falsifiers, uncertainty, resource budget, status and supersession reason.
- `PlanDAGManifest`: step IDs, dependencies, readiness, concurrency ceiling, critical path, resource vector, cancellation and retry semantics.
- `EvidenceClaimRecord`: claim ID, source artifact/span, acquisition method/time, publisher, source authority, transformation lineage, temporal scope, independence group, contradiction links and review status.
- `ResultAdmissionReceipt`: output digest, claims, evidence refs, verifier profile/build, method, scope, policy epoch, limitations and signature.
- `IndependenceProfile`: model/provider/version, prompt/template, corpus, tools, operator, source overlap and shared failure domains.
- `EvaluationProtocol`: predeclared criteria, artifact digest, dataset partitions, evaluator roles, access policy, environment, case manifest and leakage rules.
- `CaseExecutionReceipt`: case ID, holdout partition, artifact under test, runner/evaluator identity, environment, inputs, raw outcome, timestamp and attestation.
- `SpecialistQualificationManifest`: domain, identity, competency evidence, benchmark, jurisdiction, scope, expiry, revocation and accountable reviewer.
- `ForecastCalibrationReceipt`: target definition, horizon, base rate, calibration data, metric values, uncertainty, drift status and applicability domain.
- `ModelValidityProfile`: domain/system boundary, equations/behavior, version, assumptions, calibration/validation data, scope, resolution, uncertainty and known failure regions.
- `WorldSnapshot` / `ExperimentManifest`: initial state, source lineage, kernel/model versions, interventions, parameters, seeds, environment, budgets and reproducibility anchors.
- `RealityObservationReceipt`: independently authenticated observation, raw media digest, custody, calibration, measurement method, uncertainty and reviewer.
- `SystemScopeAuthorization`: target ownership, exact asset/version, passive/active permission, techniques, time window, limits, data handling and stop conditions.
- `MediaCustodyRecord`: original digest, source/device, capture time, consent/rights, transformations, derived artifacts, alignment and retention.
- `ImpactMeasurementReceipt`: baseline/counterfactual, unit, methodology, geography, interval, source, uncertainty, reviewer and anti-double-counting identity.

## 6. New bounded gap entries

- `GAP-HYPOTHESIS-ALTERNATIVE-AND-FALSIFICATION-LIFECYCLE`
- `GAP-HYPERSYNTH-DEPENDENCY-DAG-CONCURRENCY-AND-BUDGET-SEPARATION`
- `GAP-SIMULATOR-SEMANTIC-MODEL-AND-VALIDITY-EVIDENCE`
- `GAP-AGENT-CRITIQUE-INDEPENDENCE-AND-EVIDENCE-LINEAGE`
- `GAP-EVALUATION-HOLDOUT-ISOLATION-AND-CASE-EXECUTION`
- `GAP-FORECAST-PROBABILITY-CALIBRATION-AND-DRIFT`
- `GAP-MIRROR-WORLD-REALITY-DATA-CALIBRATION-LIFECYCLE`
- `GAP-MULTIMODAL-SOURCE-CUSTODY-AND-TRANSFORMATION-LINEAGE`
- `GAP-SPECIALIST-QUALIFICATION-AND-DOMAIN-COVERAGE`

## 7. Closure order and acceptance evidence

1. Freeze vocabulary and typed IDs for claim, branch, evidence, model, experiment, evaluation, observation and impact.
2. Define lifecycle/state transitions and ownership for each record; include rejection, contradiction, expiry, revocation, supersession and recovery.
3. Establish source/evaluator/model independence and evidence-custody requirements.
4. Define branch/DAG scheduling, deterministic replay and resource accounting separately from agent count.
5. Define model validity/calibration/uncertainty and Reality Bridge admission by domain.
6. Define holdout isolation and evaluation receipts before any performance tuning against a final benchmark.
7. Map the contracts to all twelve workstreams and existing ADRs; resolve owners and conflicts before implementation.
8. Only after W01–W12 architecture closure, integrate adapters and run end-to-end tests against the frozen baseline and approved acceptance matrix.

No stream is marked complete by this audit. W01–W12 remain PARTIAL.
