# NORYX7 — Cognitive Branching, Formal Evidence, MIRROR WORLD and Systems Understanding Reconciliation

**Review date:** 2026-11-24  
**Reviewed branch snapshot:** `e44a7547c7c67ac7e0c8e916fa67cd0282940f38`  
**Status:** architecture-only source reconciliation; no runtime, tests, dependencies, workflows or deployment changed.  
**Scope:** concurrent architecture review across W01–W12, with emphasis on HYPERSYNTH, NEXUS/FRL, MIRROR WORLD, authorized systems understanding, surfaces/terminal, specialist domains and ecosystem governance.

## 1. Executive finding

The repository contains meaningful bounded primitives, but the current implementation and the intended NORYX7 system must remain distinct. The inspected HYPERSYNTH path coordinates decomposition, specialist routing, planning, one hypothesis per plan step, simulation checks, allocation, sequential execution, result verification and metacognitive reflection. This is a real orchestration path, but it is not yet a general branching-search engine, concurrent DAG executor, calibrated world simulator or independently evidenced reasoning system.

The architecture therefore needs a common artifact and lifecycle model connecting:
- task/goal and execution identity;
- alternative hypotheses and dependency-aware plans;
- source-anchored claims and formal proof artifacts;
- model/simulation manifests and calibration evidence;
- authorized system observations and reconstruction artifacts;
- specialist qualification and scope;
- device/browser/terminal execution boundaries;
- resource placement and operational telemetry;
- community, financial and environmental outcome evidence.

No single subsystem may infer authority, truth, qualification or real-world permission from a label, confidence number, simulation result, agent identity string or successful local execution.

## 2. Bounded source observations

### 2.1 HYPERSYNTH and branching cognition — W02/W04/W05/W06/W10

Inspected:
- `core/hypersynth.py`
- `core/reasoning.py`
- `core/metacognition.py`
- `core/verification.py`
- `core/agent_core.py`
- `core/agent_fabric.py`
- `jarvis/core/orchestrator.py`

Observed boundaries:
1. HYPERSYNTH binds an execution ID, verifies the task contract, routes a specialist domain, decomposes the task, routes subtasks, builds context, verifies a plan, generates hypotheses, runs the internal simulator, allocates agents and executes assignments.
2. The inspected `HypothesisEngine.generate` maps each plan step to one hypothesis whose statement is the step objective and whose basis is the step ID. It does not itself create a tree of competing explanations, preserve alternative causal graphs or manage branch pruning/reopening.
3. `InternalSimulator` is a bounded internal feasibility primitive; it is not evidence of calibrated physical, economic, ecological or cyber-physical simulation.
4. The HYPERSYNTH assignment loop is sequential. `max_agents` also bounds accepted plan length in this path; agent count, branch count, concurrency and scheduler capacity are distinct concepts and must not be conflated.
5. `VerificationEngine.verify_output` checks non-null/non-empty output. Other contract and identity checks do not by themselves establish semantic entailment, factual truth or source authenticity.
6. Metacognitive reflection exposes counts and a confidence value and has a challenge-verifier seam. These are not automatically calibrated probabilities or proof of verifier independence.
7. Native `AgentFabric` binds an AgentCore, AgentIdentity and skills, and invokes an injected principal authorization callback. This does not establish an externally governed issuer, specialist qualification, distributed lease or independent evidence.
8. JARVIS has a separate request/plan/policy orchestration path. A canonical adapter contract is still required; the two paths must not silently become competing policy or state authorities.

Architecture requirements:
- represent a hypothesis as a versioned artifact with parent/child branch IDs, claim IDs, assumptions, source references, method, predicted observations, falsifiers, uncertainty, resource budget and lifecycle state;
- preserve rejected, contradicted, suspended and superseded branches with reasons; never erase a contradiction merely to select a winner;
- distinguish exploration branches from executable action plans;
- make DAG dependencies, critical path, concurrency limits, cancellation, fairness, leases, retries and uncertain side effects explicit;
- separate model/provider diversity from independent evidence; consensus requires lineage and failure-domain analysis;
- bind every final claim to evidence and scope, not merely to the agent that emitted it.

### 2.2 NEXUS, FRL and evidence — W01/W03/W06/W09/W10

Inspected:
- `core/verification.py`
- `core/evaluation_campaign.py`
- `architecture/NORYX7_CROSS_CUTTING_ARCHITECTURE_CONTRACTS.md`
- `architecture/NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md`

Observed boundaries:
- The evaluation campaign module generates bounded deterministic local cases and manifests; generation is not execution, and a holdout manifest is not proof of an independently run, leakage-safe campaign.
- The architecture defines NEXUS as typed semantic data and FRL as formal proof/proposition/checker artifact management. Neither is to become an action authority.
- A formal proof can establish only the exact proposition under the exact axioms, definitions, theory, checker and artifact scope. It cannot prove that an empirical source was faithfully formalized.
- Empirical observation, source-reported claims, derived claims, formal proof, simulation, hypothesis and disputed evidence must remain separate epistemic classes.
- A checker unavailable, timed out, invalid or untrusted must not produce an accepted proof state.

Required shared evidence envelope:
`claim_id, claim_version, proposition_or_statement, scope, source_artifacts, source_offsets, acquisition_time, transformations, method, assumptions, units, uncertainty, contradictions, reviewer, checker_or_model_manifest, result, expiry, supersession`.

Required lifecycle:
`DISCOVER → ACQUIRE → AUTHENTICATE → NORMALIZE → EXTRACT → ANCHOR → ASSESS → CORROBORATE/CONTRADICT → REVIEW → ADMIT_FOR_SCOPE → EXPIRE_OR_REVISE`.

### 2.3 MIRROR WORLD and model validity — W03/W05/W06/W07/W09/W10/W11

Inspected:
- `architecture/NORYX7_MIRROR_WORLD_ARCHITECTURE.md`
- `core/reasoning.py`
- `core/multimodal.py`
- `ecosystem/global_scale.py`

The MIRROR WORLD specification correctly distinguishes synthetic web, software/infrastructure, cyber range, physical/engineering, socio-economic, environmental and composite worlds. It also specifies isolation, reproducibility, model plurality, causal discipline and a non-actuating Reality Bridge.

Open contracts:
- model registry and immutable model manifest;
- explicit state variables, units, equations/algorithms, assumptions and boundary conditions;
- observation dataset identity, quality, temporal coverage and licensing;
- calibration/validation split, independent validation and leakage prevention;
- uncertainty propagation, sensitivity, identifiability and out-of-distribution envelope;
- model validity scope, expiry, drift detection and downgrade/rejection;
- reproducible experiment snapshot, seed, kernel/build, resource budget and event log;
- separate approval for any Reality Bridge operation, with safety case and rollback/compensation path.

A model may be fit for one bounded experiment and invalid for another. Numerical agreement on one dataset is not universal validity. Simulation success never grants real-world action authority.

### 2.4 Authorized systems understanding / reverse engineering — W06/W07/W08/W09/W10

The architecture document describes authorized observation and analysis, isolated workspaces and MIRROR WORLD. A direct fetch of `core/reverse_engineering.py` on the reviewed branch returned 404. This is a bounded path-level observation only; it is **not** a claim that no reverse-engineering functionality exists elsewhere in the repository.

Required capability decomposition:
1. scope and authorization manifest (owner, target, purpose, jurisdiction, allowed methods, time window);
2. passive acquisition (files, package metadata, exposed interfaces, protocol traces, logs, documented APIs);
3. active probing only where explicitly authorized and rate/budget bounded;
4. artifact custody (original bytes, hashes, signatures, timestamps, chain of custody);
5. static/dynamic analysis in isolated sandboxes;
6. dependency, component, protocol and data-flow graph reconstruction;
7. behavioral hypotheses and differential experiments;
8. vulnerability/weakness reporting with confidence and reproducibility;
9. remediation proposals and regression artifacts;
10. deletion/retention and disclosure workflow.

Hard boundaries: no unauthorized access, credential theft, persistence, evasion, exfiltration, destructive testing or copying of protected implementation/IP. Reconstructed behavior must be labeled as observed, inferred or hypothesized. The system must support interoperability/security analysis without representing a behavioral approximation as source-code equivalence.

### 2.5 Surfaces, browser, Android/iOS, terminal and offline — W01/W02/W05/W08/W09/W11

Inspected:
- `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md`
- `architecture/NORYX7_CROSS_CUTTING_ARCHITECTURE_CONTRACTS.md`
- `jarvis/core/orchestrator.py`
- `core/agent_core.py`

The PowerShell/Cloud Terminal file is a target architecture specification, not proof of a deployed terminal runtime. The inspected JARVIS orchestration path has its own request/plan/policy boundary. Device/browser/terminal surfaces must remain adapters and must not create local policy, identity, memory or state authorities.

Required surface contract:
- enrolled device/workload identity and attestation freshness;
- signed, scoped, expiring capabilities and remote revocation;
- request/execution/operation/attempt IDs and idempotency;
- explicit shell/tool allowlist, filesystem namespace, process limits and network egress;
- ephemeral vs persistent storage boundary and secret injection;
- artifact import/export provenance and malware/content inspection;
- session interruption, offline outbox, replay and indeterminate-effect reconciliation;
- audit correlation and human approval for high-impact operations.

### 2.6 Specialist domains — W06/W09/W10/W11

The domain assurance specification requires manifests containing domain/version, geography/time validity, source classes, ontology/units, method/model validity, uncertainty, independent checks, prohibited inference, escalation, privacy/licensing, budgets and lifecycle.

This must become a qualification system rather than a skill-name system:
- qualification authority and reviewer independence;
- evidence of competence and validation corpus;
- scope/jurisdiction/temporal validity;
- permitted advisory vs execution roles;
- expiry, suspension, appeal and conflict-of-interest handling;
- high-impact human/expert sign-off;
- monitoring of drift and adverse outcomes.

Medicine, structural engineering, energy infrastructure, law, finance, agriculture and environmental remediation require different evidence and escalation policies. A general specialist label cannot grant regulated authority.

### 2.7 Global placement and operations — W02/W05/W08/W09/W11

Inspected:
- `core/resource_router.py`
- `ecosystem/global_scale.py`

The core DEVICE/EDGE/CLOUD router is threshold-based over complexity, privacy and latency. The global-scale module explicitly describes bounded control-plane primitives rather than a production cloud, database, broker, scheduler or network fabric. It includes health/degradation and residency-aware region selection primitives, but these do not alone prove live capacity, provider health or durable placement.

A canonical placement decision must jointly evaluate hard constraints before optimization:
- privacy classification, tenant and jurisdiction/data residency;
- capability and model compatibility;
- attestation, trust and software version;
- live health, capacity, queue, deadlines and failure domains;
- latency, bandwidth and availability;
- monetary cost, energy/carbon and hardware wear;
- locality, redundancy, disaster recovery and data gravity.

Hard constraints must never be traded away for lower cost or latency. Placement output is a decision record with inputs, policy version, candidate exclusions, score breakdown, expiry and re-evaluation trigger.

### 2.8 Ecosystem, finance and environmental impact — W03/W06/W09/W10/W11/W12

The product/community architecture must distinguish:
- activity counts from verified outcomes;
- pledged funds from received, restricted, available and disbursed funds;
- user identity from eligibility and beneficiary status;
- a modeled environmental benefit from a measured net outcome.

Required contracts include segregated project funds, double-entry ledger, reconciliation, refunds/disputes, approval limits, conflicts of interest, beneficiary safeguards, contributor rights, audit and exit rules. Environmental claims require baseline, system boundary, counterfactual, additionality, leakage, rebound effects, uncertainty, permanence where relevant and independent measurement. Agriculture/recycling/cleanup projects need traceable material flows and safety controls, not just participation counters.

## 3. Cross-workstream dependency map

| Shared contract | Owning streams | Required consumers |
|---|---|---|
| Principal, issuer, capability and revocation | W01/W09 | W02/W04/W05/W08/W10/W12 |
| Canonical task/branch/plan/execution/operation IDs | W02/W04 | W03/W05/W06/W08/W11 |
| Claim/evidence/provenance envelope | W06 | W03/W04/W07/W10/W11/W12 |
| Model manifest and calibration evidence | W07/W10 | W04/W05/W06/W11 |
| Authorized observation/artifact custody | W08/W09 | W06/W07/W10 |
| Placement constraints and cost/energy accounting | W05/W11 | W02/W04/W07/W08/W12 |
| Domain qualification and escalation | W10 | W04/W06/W07/W12 |
| Durable audit, recovery and effect reconciliation | W02/W03/W09/W11 | all streams |
| Funds and verified impact accounting | W12 | W06/W09/W10/W11 |

## 4. Decisions to consolidate into existing ADRs

No new independent ADR series is created.

| Existing ADR | Reconciliation required | Status |
|---|---|---|
| B79/B80/B85/B87 | Canonical branch, plan, task, step, execution, lease and attempt lifecycle; DAG coverage and cancellation | OPEN |
| B86/B104 | Retry, idempotency, outbox and uncertain external-effect reconciliation | OPEN |
| B88/B90/B97 | Independent consensus, claim/evidence classes, source lineage and semantic admission | OPEN |
| B91 | Evaluation campaign execution evidence, holdout custody, evaluator identity and leakage prevention | OPEN |
| B92/B93/B100 | Forecast/model calibration, MIRROR WORLD validity, uncertainty/OOD and Reality Bridge | OPEN |
| B94/B97 | Multimodal custody, transformation lineage, consent and source anchoring | OPEN |
| B76/B99 | Specialist qualification, jurisdiction, scope, expiry and reviewer independence | OPEN |
| B71/B96/B98 | Authorized acquisition, egress mediation, content isolation and provider/source identity | OPEN |
| B72/B77/B89 | Artifact/build provenance, signed model/kernel manifests and evidence-backed freeze | OPEN |
| B81/B103 | Scoped memory, experiment snapshots, retention, deletion and reproducibility | OPEN |
| B83/B84/B101 | Segregated funds, governance, safeguards and independently verified environmental outcomes | OPEN |
| B95 | Placement/provider adapter, residency, live capacity and production infrastructure contracts | OPEN |

## 5. W01–W12 impact

- **W01:** identity/authority must bind every branch, observation, model, tool and terminal operation to a principal and scope.
- **W02:** HYPERSYNTH and JARVIS require one canonical lifecycle without collapsing distinct adapters prematurely.
- **W03:** branch state, evidence, media, experiment snapshots and audit require scoped durable storage and deletion semantics.
- **W04:** agent assignment must separate skill, qualification, identity, lease, independence and result admission.
- **W05:** resource placement must include hard trust/residency constraints plus live cost, energy, capacity and health.
- **W06:** NEXUS/FRL/evidence need typed claims, exact proof scope, source lineage and evaluation integrity.
- **W07:** MIRROR WORLD needs calibrated model manifests, reproducible experiments and a non-actuating Reality Bridge.
- **W08:** browser/device/terminal/offline surfaces need one capability and artifact boundary.
- **W09:** cryptographic authority, safe egress, isolation, artifact custody and audit apply to all acquisition/execution.
- **W10:** domain specialists require independent qualification, scope and escalation.
- **W11:** observability, SLOs, resource budgets, model drift, recovery and fairness must be measurable.
- **W12:** business/community/finance/environmental workflows require real ledger and independently measured outcome contracts.

All W01–W12 remain **PARTIAL**. This document does not claim integration, test execution, production readiness or architecture freeze.

## 6. Next architecture-only work

1. Build a repository-wide symbol/call-site graph for HYPERSYNTH, NEXUS/FRL, agent fabrics, terminal, reverse-engineering and MIRROR WORLD references.
2. Reconcile branch/hypothesis lifecycle with task/plan/step/execution/operation identifiers and existing ADRs.
3. Define the single claim/evidence/model/artifact envelope and its lifecycle states.
4. Map every surface's authority and execution boundary, including offline and terminal.
5. Complete domain qualification and W12 funds/impact contracts.
6. Only after all workstream contracts are reviewed, decide architecture freeze; integration and comprehensive verification remain later phases.
