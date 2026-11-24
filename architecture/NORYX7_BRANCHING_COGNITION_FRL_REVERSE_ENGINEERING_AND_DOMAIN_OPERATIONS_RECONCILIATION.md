# NORYX7 — Branching Cognition, Formal Evidence, Reverse Engineering and Domain Operations Reconciliation

**Status:** source-reconciled architecture proposal; OPEN / NOT FROZEN  
**Source snapshot:** PR #212 head `e44a7547c7c67ac7e0c8e916fa67cd0282940f38` (2026-11-24)  
**Scope:** parallel continuation across W01–W12; documentation only  
**Canonical plane constraint:** ADR-001 remains authoritative: exactly 18 canonical planes. This document adds no plane and creates no new ADR series.

## 1. Purpose and review boundary

This pass deepens four coupled areas that were still described mostly as target architecture: (1) HYPERSYNTH branching and contradiction management; (2) NEXUS/FRL and mathematical proof/evidence boundaries; (3) authorized reverse engineering and secure terminal surfaces; and (4) specialist-domain qualification and environmental/community outcome operations.

The source review is bounded to the named files and recursive tree at the exact snapshot above. It is not a complete audit of every caller, deployment, external connector or production environment. Presence of an interface or architecture document is not evidence of operational deployment.

No runtime, test, dependency, workflow, deployment, release, frozen baseline or merge was changed. No integration or test campaign was run.

## 2. HYPERSYNTH: from bounded linear hypotheses to explicit branching

### 2.1 Observed implementation boundary

The inspected source shows:
- `core/decomposition.py` creates a bounded ordered subtask tuple and validates references against earlier task IDs; it is not a general search-space explorer.
- `core/planning.py` creates a bounded plan and typed action/risk/dependency fields.
- `core/reasoning.py` currently emits one hypothesis per plan step. The hypothesis statement is the step objective and its basis is the step ID.
- `InternalSimulator` currently checks that a hypothesis is structurally present and associated with the task; it does not execute a domain model or compare competing predicted outcomes.
- `core/hypersynth.py` wires the stages into a bounded pipeline and constrains the default planner budget using `min(max_steps, max_agents)`.
- `core/metacognition.py` checks one-to-one identity/count/order relationships between plan, hypotheses, simulations and results. This is useful pipeline integrity, not proof that alternatives were explored or that confidence is calibrated.

The current source therefore supports bounded decomposition and a linear plan-aligned hypothesis collection. It does not yet establish the full lateral/branching exploration model described in the product vision.

### 2.2 Proposed branch model

Introduce a versioned architecture contract (not runtime code in this phase) for a `HypothesisBranch` with:
- stable branch ID, task/execution ID, parent branch ID and branch generation;
- explicit proposition/decision question and typed assumptions;
- source/evidence references and their evidence classes;
- proposed method/model and required specialist capabilities;
- dependency edges and mutually exclusive / compatible alternatives;
- resource budget, deadline, stop conditions and branch status;
- predicted observations/outcomes with units and uncertainty where applicable;
- contradiction links, counterexamples and unresolved premises;
- pruning rationale and reproducibility seed/version where stochastic search is used.

A branch is a candidate, not a belief or an action. Branch creation cannot grant tools, network access, credentials or actuation authority.

### 2.3 Branch lifecycle and merge policy

Recommended lifecycle:
`PROPOSED → CONTRACT_CHECKED → EVIDENCE_BOUND → BUDGET_ADMITTED → EXPLORED → CHALLENGED → COMPARED → RETAINED | PRUNED | BLOCKED | UNKNOWN`.

Branch expansion must be bounded by explicit limits on depth, width, total nodes, tokens/compute, wall time, external calls and specialist invocations. The scheduler must preserve dependency constraints and reserve capacity fairly; exhaustion returns `BUDGET_EXHAUSTED`, not a silently truncated success.

Branches may merge only when their assumptions, scope, evidence lineage and semantic outputs are compatible. Contradictory branches remain visible as dissent; majority vote, repeated model output or equal strings cannot erase them. A merge record must identify the rule, inputs, discarded alternatives and reviewer/validator.

The user-facing output should expose concise decision-relevant alternatives, assumptions, evidence and uncertainty—not hidden private reasoning traces. Internal search traces are not a substitute for auditable claims.

### 2.4 Cross-agent independence

Agent count is not independence. Independence assessment must cover model/provider lineage, shared prompts, common training or retrieval sources, tools, datasets, execution environment, operator, verifier and failure domain. Independence groups and correlated failure assumptions must be explicit before consensus or evaluation aggregation.

## 3. NEXUS / FRL / Mathematical Intelligence Fabric

### 3.1 Source observations

- `core/universal_intelligence.py` defines evidence and domain-assessment records with source/claim strings, numeric strength, confidence, uncertainty and contradiction fields. Shape/range validation does not authenticate the source, anchor a claim to source spans or calibrate a probability.
- `core/subtask_verification.py` requires exact route/result coverage and an `agent_result` verification marker, then records output strings and a boolean verified field. This is a commit-eligibility structure, not source-grounded semantic entailment.
- `core/evaluation.py` aggregates locally supplied dimension results. `core/evaluation_campaign.py` deterministically creates synthetic cases and a holdout manifest, but explicitly does not execute the cases or infer the truth of recorded results.
- `EvaluationCampaign.approve` checks that the set of required dimensions is present and all recorded results pass. The inspected contract does not bind results to a signed evaluator identity, immutable campaign execution record, one-result-per-case ledger or independent evidence custody.
- `architecture/NORYX7_CRYPTOGRAPHIC_AND_MATHEMATICAL_INTELLIGENCE_ARCHITECTURE.md` describes a Mathematical Intelligence Fabric and proof-carrying theorem capsules as architecture. In the inspected source path inventory, no dedicated general FRL proof-kernel/runtime is established by that document.

### 3.2 Canonical evidence graph

NEXUS should distinguish immutable source artifacts from claims and derived interpretations. Minimum node types:
- SourceArtifact and SourceVersion;
- SourceSpan / Observation / Measurement;
- Claim with exact proposition, scope, jurisdiction and valid-time interval;
- Inference with premises, method/rule version and uncertainty propagation;
- FormalProof with formal statement, theory, axioms, proof object and checker;
- EmpiricalResult with protocol, sample, controls, statistics and replication;
- SimulationResult with model manifest, seed, parameters and calibration status;
- ExpertReview with qualification, scope and conflict disclosure;
- DecisionRecord with policy, accepted evidence set, dissent, expiry and appeal.

Edges must be typed (supports, contradicts, derives-from, formalizes, measures, reproduces, supersedes, applies-under). A source citation must resolve to a stable version and, where applicable, exact page/paragraph/timecode/byte range. Corrections create versioned successor records; they do not silently rewrite historical evidence.

### 3.3 FRL assurance outcomes

Formal reasoning outcomes are non-interchangeable:
`PROVED`, `DISPROVED`, `UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, `CHECKER_ERROR`, `INVALID_CERTIFICATE`.

A proof admission package binds the exact proposition, formal language, theory/axioms, dependencies, proof artifact digest, checker and trusted-kernel versions, resource limits, termination result and independent replay policy. A failed proof attempt is not a counterexample unless a counterexample is itself checked.

Formal proof establishes a proposition relative to its formal assumptions. It does not establish that an empirical dataset is accurate, that a physical model represents reality, or that a real-world system satisfies the formalized assumptions.

### 3.4 Evaluation campaign integrity

A campaign contract should bind:
- immutable manifest and campaign/version ID;
- case IDs, seed, split and holdout custody;
- evaluator principal, workload identity and qualification;
- exact artifact/model/prompt/tool versions;
- per-case inputs, outputs, metrics and failure records;
- independent result signature and provenance;
- duplicate/replay policy and missing-case accounting;
- statistical plan, confidence intervals and subgroup coverage;
- benchmark contamination/leakage controls;
- reproducibility and independent audit disposition.

Missing, duplicated, unexecuted or unauthenticated cases cannot be counted as passing. An aggregate score cannot hide a failed safety/security dimension or an untested subgroup.

## 4. Authorized systems reverse engineering

### 4.1 Existing boundary

The inspected source contains `core/cyber_range.py`, whose targets are explicitly synthetic and sandbox-scoped and whose actions are symbolic. `core/sandbox.py` is fail-closed for privileged host mutation, core access and real secrets. These are defensive building blocks, not a general reverse-engineering workbench.

The repository architecture includes software/system engineering and protocol analysis concepts, but the inspected source inventory does not establish a dedicated end-to-end reverse-engineering runtime, parser corpus, dynamic instrumentation service or protocol reconstruction engine.

### 4.2 Authorized RE workbench contract

A reverse-engineering project must begin with a signed scope manifest:
- authorizing owner/principal and proof of authority;
- target asset, version, hashes and allowed interfaces;
- permitted acquisition methods and time window;
- explicit exclusions (third-party targets, production credentials, personal data, destructive tests);
- permitted static/dynamic methods, rate and resource budgets;
- data-handling, retention, disclosure and deletion rules;
- stop conditions, incident contact and review owner.

Proposed stages:
1. **Acquire:** owner-provided binaries/source/configuration, public specifications or explicitly authorized observations; preserve originals and hashes.
2. **Inventory:** file formats, dependencies, build metadata, symbols, licenses and provenance.
3. **Static analysis:** control/data flow, call graph, dependency graph, API surfaces, configuration and cryptographic boundary mapping.
4. **Dynamic observation:** only in isolated, instrumented sandboxes with synthetic identities/data and no ambient credentials or unrestricted egress.
5. **Protocol reconstruction:** state machines, message schemas, framing, version negotiation, error semantics and conformance vectors.
6. **Differential analysis:** compare versions/implementations using reproducible fixtures and documented deviations.
7. **Security assessment:** classify weakness hypotheses and validate only within authorized scope.
8. **Evidence/review:** attach exact artifact offsets, trace IDs, reproduction steps, tool versions, confidence and independent review.
9. **Disclosure/remediation:** responsible disclosure, patch proposals, regression specifications and owner-approved retest.

The output is an interoperable behavioral specification or compatibility layer, not copied proprietary source or an assertion of ownership. Do not bypass access controls, exfiltrate secrets, target third parties, or convert simulation authorization into real-target authorization.

### 4.3 Protocol and software understanding outputs

A system model should represent components, interfaces, state transitions, trust boundaries, dependencies, data classification, error behavior and observed invariants. Every edge is tagged as documented, statically inferred, dynamically observed, hypothesized or unknown. Confidence cannot be raised merely because multiple agents repeat the same inference.

## 5. Terminal, browser and polyglot surfaces

### 5.1 PowerShell / Cloud Terminal

`architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md` specifies a terminal-session and local/remote job architecture. The inspected source inventory does not establish a dedicated PowerShell/Cloud Terminal runtime implementation. It must remain classified as target architecture until a concrete host, session broker, sandbox adapter and policy/audit integration are evidenced.

The terminal contract must bind session, device, principal, shell, working directory, environment, capabilities, resource budget, deadline, network policy, persistence mode and attestation. Command parsing, policy evaluation, sandbox admission, execution, output capture, verification and audit must be one non-bypassable lifecycle. Shell aliases, scripts, modules, background jobs and remoting cannot create authority not present in the session grant.

Persistent home storage is separate from ephemeral compute. Secret injection is scoped and non-exportable by default. Remote execution requires target attestation, host-key binding, audience-bound session, expiry, revocation, per-command capability and durable receipt.

### 5.2 Browser / mobile / polyglot

`ecosystem/browser_isolation.py` is a static source-marker scan. It is not runtime WebView hardening, network egress proof, Android/iOS permission review, certificate pinning, exploit resistance or device attestation. Each surface requires a threat model and a shared identity/request/consent/receipt contract.

Cross-language interoperability requires canonical schemas, explicit numeric/time/null/Unicode rules, version negotiation, unknown-field policy, signature transcript binding, conformance vectors and negative test vectors. Matching digests only prove agreement on canonical bytes; they do not prove semantic equivalence.

## 6. Specialist domains and real-world assurance

### 6.1 Qualification is not a route label

The specialist catalog must distinguish a declared domain route from a qualified capability. Each specialist package needs:
- domain/subdomain, jurisdiction and time validity;
- ontology, units, coordinate and terminology conventions;
- source admission/exclusion rules and licensing;
- methods, model/tool versions and validity envelope;
- qualification evidence, evaluator and independent review;
- calibration, known failure modes and uncertainty;
- prohibited inference and escalation triggers;
- privacy, safety, retention and resource budget;
- expiry, suspension, revocation and appeal.

High-impact medical, legal, financial, structural, energy and environmental outputs require human/domain expert escalation according to risk. A specialist cannot authorize its own actions or approve its own evidence.

### 6.2 MIRROR WORLD model admission

The existing MIRROR WORLD architecture remains a target architecture. A model package must bind system boundary, state variables, units, equations/behavior rules, parameter provenance, calibration dataset, independent validation, sensitivity, uncertainty, model discrepancy, OOD envelope, version and expiry. Correlation, scenario plausibility and visual fidelity do not establish causality or predictive validity.

The Reality Bridge remains non-actuating by default. Real actuation requires a separate device/asset principal, scoped grant, safety interlocks, precondition checks, operator confirmation, independent feedback, bounded command and emergency-stop path.

### 6.3 Environmental, agriculture and community projects

For each intervention, preserve baseline, counterfactual, additionality, geographic/system boundary, leakage, rebound, lifecycle effects, uncertainty, sampling and independent verifier. Distinguish activity/output (hours, funds, kilograms collected, trees planted) from outcome/net impact (verified reduction in exposure, leakage, emissions or ecosystem damage). Do not publish one unqualified impact score.

Funding flows must distinguish donor funds, restricted project funds, participant compensation, supplier payments, platform revenue and refundable balances. Time contribution is not an investment or guaranteed income. Work assignment requires voluntary terms, training, PPE, insurance/coverage where applicable, stop-work authority, grievance and fair compensation.

## 7. Cross-workstream dependency matrix

| Workstream | New source-grounded delta | Contract still required | Status |
|---|---|---|---|
| W01 Identity | Evaluator, reviewer, RE operator, terminal session and domain specialist need scoped principal context | Issuer/tenant/device/session, role, qualification and revocation binding | PARTIAL |
| W02 Runtime | HYPERSYNTH is bounded/linear; terminal and RE lifecycles are specified more than implemented | Branch/operation state machine, cancellation, budget exhaustion and effect certainty | PARTIAL |
| W03 Memory | Evidence graph requires immutable source/version and correction lineage | Scoped custody, consent, retention, deletion/tombstone and legal hold | PARTIAL |
| W04 Agent Fabric | Branch and specialist labels do not prove independence/qualification | Branch lineage, capability delegation, qualified admission and dissent preservation | PARTIAL |
| W05 Routing | Branch exploration, proof checking and simulation compete for resources | Priority/fairness, live capacity, energy/cost, residency and reserved verifier capacity | PARTIAL |
| W06 Evidence | Evidence strength/verified markers are structural and unauthenticated by themselves | Claim graph, source spans, FRL proof package and campaign integrity | PARTIAL |
| W07 MIRROR WORLD | Simulator primitive is not domain-calibrated world model | Model manifest, validation, uncertainty/OOD and non-actuating bridge | PARTIAL |
| W08 Surfaces | Terminal is architecture-only; browser gate is static; cyber range is synthetic | Shared surface contract, sandbox attestation, consent and durable receipts | PARTIAL |
| W09 Security | Sandbox defaults deny privileged flags; authority and RE scope remain separate | Signed scope/grants, egress enforcement, secrets isolation and audit custody | PARTIAL |
| W10 Domains | Domain route/evidence shape is not qualification | Specialist manifests, expert review, jurisdiction and expiry | PARTIAL |
| W11 Operations | Campaign manifests do not prove executed evaluations; terminal runtime not evidenced | Durable telemetry, reproducible release, incident/DR and SLO ownership | PARTIAL |
| W12 Ecosystem | Environmental/community architecture needs outcome and fund custody | Restricted ledger, safeguards, grievance, independent measurement and reconciliation | PARTIAL |

## 8. Existing decision mapping — no duplicate ADR series

Carry findings into existing proposals:
- B70–B72: durable audit, artifact/evaluator/tool provenance and release integrity;
- B75–B78, B90–B92: evidence assurance, evaluation integrity, forecast calibration and independent admission;
- B79–B80, B85–B88: principal/operation identity, dispatch, DAG/branch execution and consensus independence;
- B93, B100: model validity and Reality Bridge;
- B94, B97: multimodal custody and canonical claim/evidence lineage;
- B96, B98: safe research egress, RE acquisition boundary and untrusted content isolation;
- B99: specialist qualification and scope;
- B101: community/environmental outcome accounting;
- B102–B104: ingress identity, context isolation and durable offline/side-effect reconciliation.

All remain OPEN/PROPOSED unless explicitly approved in a separate review. This document does not change their status.

## 9. Architecture completion criteria before integration

The architecture phase is not complete until:
1. every canonical plane has authoritative owner, inputs/outputs, state, trust boundary, failure/degraded behavior and dependencies;
2. every cross-plane edge has a versioned contract, principal/authority semantics, data classification and evidence/receipt semantics;
3. every source-to-claim-to-decision path has provenance and correction/expiry behavior;
4. HYPERSYNTH branch budgets, dependencies, pruning, contradiction and merge semantics are specified;
5. FRL proof admission and empirical/simulation evidence remain non-interchangeable;
6. reverse-engineering and terminal scopes cannot escape authorization/sandbox/egress controls;
7. specialist qualification, jurisdiction and expiry are explicit;
8. MIRROR WORLD validity and Reality Bridge controls are complete;
9. W12 financial, worker-safety and environmental net-outcome boundaries are explicit;
10. architecture source ledger and gap register reconcile all claims against the same commit snapshot.

Only after architecture review should a separate integration plan define dependency order, compatibility adapters, migration, test layers, independent verification and release gates.

## 10. Explicit non-claims

This source reconciliation does not claim that branching cognition, a general FRL proof engine, production reverse engineering, a PowerShell Cloud Terminal, calibrated MIRROR WORLD, qualified medical/environmental specialists, global community ledger or deployed impact-verification service already exist. It does not establish general intelligence, correctness, safety or production readiness. W01–W12 remain PARTIAL.
