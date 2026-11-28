# NORYX7 — Agent, Evidence, Simulation, Forecast and Release Assurance Source Reconciliation

**Review date:** 2026-11-25  
**Reviewed source snapshot:** `a3c4d0676c33206f8cd81ddd9ca3be35f15af6a4`  
**Mode:** architecture-only, bounded source inspection. No runtime, tests, dependencies, workflows, deployment or frozen baseline changes.

## 1. Purpose and scope

This pass continues W01–W12 together and inspects the source-level boundary between agent selection, task delegation, subtask coverage, semantic evidence, simulation, forecasting, provider retries, dispatch receipts, browser isolation and artifact trust.

The governing distinction is:
- **declared architecture** — the behavior and contracts described in design documents;
- **source behavior** — behavior directly visible in inspected implementation;
- **operational guarantee** — requires integrated call paths, durable state, external enforcement, deployment controls and evidence beyond an individual class.

No claim in this document promotes a structural marker, local digest, synthetic simulation or successful unit-test specification into proof of factual truth or production assurance.

## 2. Architecture completeness gate: structural scope

`core/architecture_gate.py` declares 18 architecture planes and requires each plane definition to provide ten non-empty fields: contract, implementation boundary, integration boundary, trust boundary, failure semantics, resource budget, observability, recovery path, verification target and regression target.

The gate's implementation check tokenizes `implementation_boundary`, recognizes listed source-file suffixes and checks whether those paths exist in a small set of repository roots. `core/architecture_registry.py` supplies the canonical definitions.

**Interpretation:** this is a useful fail-closed structural inventory and path-presence gate. It does not inspect whether the named implementation satisfies the contract, whether the integration boundary is actually wired, whether tests execute the declared target, whether runtime composition is reachable, or whether operational guarantees exist. Therefore a passing structural gate cannot alone be interpreted as “the full architecture is implemented/complete.” The architecture closure process needs separate contract conformance, constructor/call-site, integration and acceptance-evidence gates.

## 3. Agent selection and coordination

### 3.1 AgentMesh

`core/agent_mesh.py` stores local AgentNode entries with an agent ID, role and optional personality ID. `route` filters by exact required role, sorts candidates by agent ID and returns the first.

Consequences:
- deterministic selection is reproducible;
- selection is not based on measured domain qualification, task-specific evidence, independence, trust freshness, workload, latency, cost, locality or capacity;
- the returned node does not itself establish that the selected agent is qualified or independently suitable for the task.

Role routing is a dispatch hint, not a professional qualification or authorization decision.

### 3.2 AgentCoordinator

`core/coordination.py`:
- obtains the router's available agent IDs;
- creates assignments for `plan.steps[:max_agents]`, so overflow steps are not assigned in this method;
- assigns by index modulo the available agent list;
- constructs a new execution ID in `execute`;
- builds child TaskSpec objects using each step ID;
- verifies the child task and passes execution through ActionGate;
- rechecks agent trust after execution and checks result task, agent and execution identities;
- executes the assignments in a sequential loop;
- consensus rejects duplicate agent IDs, task-identity mismatch, missing/mismatched execution identity, unverified results and any output disagreement; it accepts only exact output equality.

Positive properties: bounded assignment, action gating, child-task verification, identity checks and post-execution trust recheck.

Open semantics:
- complete plan coverage versus truncation/overflow;
- parent/child/branch/step/attempt identity and lineage;
- true concurrent execution, leases, resource reservation, cancellation, timeout, join and partial results;
- independence of agents, correlated model/provider dependencies and verifier separation;
- consensus for semantically equivalent but non-identical outputs, weighted evidence and explicit dissent;
- aggregation and state commit semantics for multi-step tasks.

Exact output equality is a narrow consensus criterion, not a general semantic consensus protocol.

### 3.3 SubtaskVerificationGate

`core/subtask_verification.py` checks route-set validity, exact subtask result coverage/order, unique task identity, completed results and a valid `agent_result` verification marker. It then sets `commit_eligible=True`.

The stored SubtaskEvidence converts the output to a string and records a boolean verification marker. This proves structural coverage under the local verifier contract, not source-grounded semantic entailment, domain correctness or external-effect completion. The aggregate commit gate must consume typed evidence and the canonical effect/verification lifecycle rather than treating this boolean as truth.

## 4. NEXUS / evidence and research boundary

The current source primitives provide structured observations, task/result verification, evidence labels/strengths and subtask coverage. They do not, by themselves, prove:
- source authenticity, authority, independence, freshness or jurisdiction;
- that an exact source span supports or contradicts a claim;
- unit, time, geography and scope compatibility;
- statistical calibration of confidence, evidence strength or uncertainty;
- independent formal proof checking or empirical validation;
- faithful extraction without selective omission.

NEXUS should be the typed semantic/evidence layer, not a synonym for a search index or an agent role. A canonical Claim/Evidence graph needs claim type (observed, source-reported, derived, formal, simulated, forecast, hypothesis, disputed, unknown), immutable source artifact identity, authenticated locator, exact span/media interval, source authority/scope, temporal validity, transformations, support/contradiction edges, independence groups, uncertainty, reviewer identity, correction/retraction and expiry.

Research acquisition requires separately mediated egress, DNS/IP/redirect policy, parser isolation, budgets, source custody, version history, retraction/correction handling and safe treatment of retrieved content as untrusted data.

## 5. MIRROR WORLD and cyber-range boundary

### 5.1 MIRROR WORLD architecture

`NORYX7_MIRROR_WORLD_ARCHITECTURE.md` defines a world-model substrate with source gateway, provenance registry, world-model registry, scenario designer, simulation orchestrator, domain kernels, synthetic browser world, cyber range, digital-twin adapters, socio-economic/environmental models, observation/measurement, experiment ledger, NEXUS bridge, formal/domain verification bridge and a separately isolated Reality Bridge.

Important design constraints are already explicit:
- simulation cannot grant authority;
- source, model, experiment, analysis and reality zones remain separated;
- simulation workers cannot call real-world services;
- model acceptance is scoped to a declared use;
- simulation outputs remain labeled simulated;
- Reality Bridge is disabled by default and requires separate authorization, safety controls and human approval for high-impact actions.

These are architecture requirements. The inspected source pass does not establish that the full domain kernels, model registry, calibrated data pipelines, experiment ledger, isolated execution plane or Reality Bridge have been implemented and deployed as one system.

### 5.2 CyberRange source

`core/cyber_range.py` declares synthetic targets, requires the target trust zone to be `sandbox`, checks an owner-authorization object and returns simulated attack-phase records. The module's own contract says it never dispatches arbitrary network code.

This is a useful safe simulation primitive. It is not evidence of:
- general-purpose protocol/system reverse engineering;
- authorized live target acquisition and observation;
- production sandboxing or network isolation outside the code-level contract;
- vulnerability validation against real systems;
- source reconstruction or semantic protocol inference.

The product capability “Systems Understanding / Reverse Engineering” therefore remains a broader architecture target. It needs explicit asset authorization, passive/active tiers, acquisition controls, instrumentation, reproducibility, IP/secret protection, evidence quality and human review.

## 6. FINCH forecast and evaluation validity

### 6.1 FINCH

`core/finch.py` contains a bounded event graph, keyword relevance ranking, severity-deviation anomaly scoring and forecast-shaped outputs. The forecast likelihood is calculated from mean supplied severity per subject; evidence consists of a bounded selection of observation IDs.

This is deterministic and inspectable, but the likelihood is not a calibrated probability. It lacks, in the inspected implementation, a declared target/event definition, temporal training/holdout protocol, calibration curve, proper scoring rules, confidence intervals, base-rate treatment, drift/OOD policy and independent field validation.

Until a forecast package passes those controls for a declared scope, its output should be represented as a heuristic hypothesis, not a reliable prediction or basis for high-impact action.

### 6.2 EvaluationCampaign

`core/evaluation_campaign.py` creates deterministic generated-case and holdout manifests from a seed and case counts. Its `record` method accepts an EvaluationMatrix, dimension, pass flag, score and evidence string; the docstring explicitly says it does not infer truth. Approval checks required dimensions and their recorded pass status.

It does not itself:
- execute the evaluation campaign;
- authenticate the evaluator or evidence producer;
- prove holdout isolation or prevent leakage;
- independently reproduce the claimed score;
- establish a CI, certification or production release result.

Campaign definition, campaign execution, evidence custody, assessor independence and release approval must remain separate lifecycle states.

## 7. Provider retry and external-effect uncertainty

`core/provider_router.py`, `core/provider_execution.py` and `core/provider_resilience.py` are separate paths:
- ProviderRouter resolves the first eligible registered provider and has an exception-based failover path;
- ProviderExecutionGateway bridges a provider to ExecutionFabric with a per-call authorization callback;
- ResilientProviderExecutor runs bounded attempts, excludes a provider after an exception and records provider/attempt/success/error type.

The resilience wrapper's exception path does not establish whether the provider performed a side effect before throwing. A new provider attempt after an ambiguous failure can duplicate an external effect unless the target operation has idempotency or reconciliation semantics.

Required canonical outcome distinctions:
1. not dispatched;
2. dispatch accepted;
3. dispatch outcome unknown;
4. provider acknowledged;
5. external effect observed;
6. effect rejected/compensated;
7. result verified;
8. state committed.

A single retry coordinator must own retry budget, idempotency key, attempt lineage, provider receipt verification and uncertain-effect reconciliation across every provider path.

## 8. Cross-front dispatch receipts

`ecosystem/dispatch_contract.py` creates a DispatchReceipt with intent, source/target fronts, execution/principal IDs, accepted flag, reason and evidence digest. `ecosystem/runtime_dispatch.py` requires an explicit principal-authorizer callback and topology check before invoking the handler.

The current handler receipt hashes `type(value)` on success or the exception type on failure. It is therefore an acceptance/handler-outcome trace, not proof of output content, provider authenticity or target-side effect. The digest is integrity of the supplied bytes, not an authenticated signer identity.

The canonical cross-front receipt must distinguish intent admission, handler invocation, returned payload digest, signer/adapter identity, external target receipt, observed effect and verified state commit. These must not be collapsed into one `accepted` boolean.

## 9. Browser isolation and software supply chain

### 9.1 Browser isolation

`ecosystem/browser_isolation.py` statically scans browser source files for forbidden markers and enforces a source-level gate. It is useful as a regression guard. It is not a runtime sandbox, OS process boundary, DNS/IP egress firewall, origin policy, download/upload control or cookie/session isolation proof. Those require runtime/platform enforcement and adversarial integration evidence.

### 9.2 Artifact supply chain

`core/supply_chain.py` verifies an Ed25519 signature over a component/version/artifact-digest manifest against a configured trusted-key set and can verify the actual artifact bytes against the digest.

This is a real cryptographic integrity primitive. It does not by itself establish:
- trusted build environment or reproducible build;
- dependency/SBOM completeness;
- signer key custody, rotation, revocation or threshold approval;
- provenance from reviewed source commit to built artifact;
- staged promotion, deployment identity, rollback and runtime attestation.

Release assurance must connect source, dependencies, builder, artifact, signer, approval, deployment and rollback evidence.

## 10. W01–W12 simultaneous impact matrix

| Workstream | Source-level finding in this pass | Required closure |
|---|---|---|
| W01 Identity/authority | Agent trust checks and principal authorizer callbacks exist in separate paths | Canonical issuer/principal/session/agent/evaluator/provider identity and revocation freshness |
| W02 Runtime/lifecycle | Agent and provider paths create distinct execution/attempt semantics | One operation/attempt/effect state machine with cancellation and crash recovery |
| W03 Memory/data | Evaluation and evidence need durable artifact/holdout custody | Immutable source/campaign artifacts, tenant scope, retention, correction and deletion |
| W04 Agent fabric | Role-first selection and coordinator paths coexist | Qualified manifest, parent-child lineage, complete DAG and independent review |
| W05 Routing/resources | Agent selection is not capacity/qualification-aware; execution sequential | Capacity leases, fair scheduling, bounded concurrency and backpressure |
| W06 Evidence/NEXUS | Structural markers and string outputs do not prove semantic support | Typed claims, source-span entailment, contradiction graph, provenance and calibrated uncertainty |
| W07 MIRROR WORLD | Detailed architecture exists; source does not establish calibrated full stack | Domain kernels, model registry, holdout, calibration, OOD and isolated Reality Bridge |
| W08 Interfaces/edge/cloud | Dispatch and browser gates are separate surface primitives | Unified intent, consent, authority, effect receipts and runtime isolation |
| W09 Security/crypto | Signed artifact manifest and static browser gate exist | Egress enforcement, key lifecycle, trusted build chain, signed effect receipts and durable audit |
| W10 Specialist domains | Role/domain labels and heuristic forecast outputs exist | Qualification evidence, jurisdiction, independent assessor, expiry and domain calibration |
| W11 Operations | Campaign manifest and local receipt primitives exist | Campaign execution, observability, SLOs, incident response, DR and source-to-deployment provenance |
| W12 Ecosystem/impact | No source evidence in this pass establishes independent field-impact operations | Segregated accounting, independent baselines, counterfactuals, grievance and verified outcome records |

All W01–W12 remain **PARTIAL**.

## 11. Exact source anchors (blob SHA)

| Source | Blob SHA |
|---|---|
| `core/architecture_gate.py` | `ed2e748821c0389672c747e9568b170de684c797` |
| `core/architecture_registry.py` | `2b90f6705be0e6ccf2474e94962c0d0c9539df43` |
| `core/agent_mesh.py` | `25c9162750708e53742862f9f413fdf5200ca08f` |
| `core/coordination.py` | `c5743872a5b50765db04e4a42739e9ad238ad983` |
| `core/subtask_verification.py` | `2980638a44062d8e92f2941822cb30105a697327` |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` |
| `core/evaluation.py` | `df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e` |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` |
| `ecosystem/browser_isolation.py` | `73f69b55f7bb6335d6e9294c7d48ebac1868991a` |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` |
| `ecosystem/runtime_dispatch.py` | `9f4f628c322aabb571fce64d54c3d6740cb142fd` |
| `architecture/NORYX7_MIRROR_WORLD_ARCHITECTURE.md` | `61d53f8a47dd5b03e5988fc8f7888d6f337dc993` |
| `architecture/NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md` | `3c88133795ab5aa944b52572b2fc400d89ef9c45` |
| `architecture/NORYX7_NEXUS_RESEARCH_SPECIALIST_DOMAINS_AND_IMPACT_RECONCILIATION.md` | `9fad1e90f818b572d0cbe4bdfd05cf46ca483c9f` |
| `architecture/NORYX7_AGENT_EVIDENCE_MIRROR_WORLD_AND_GLOBAL_IMPACT_RECONCILIATION.md` | `e2ee98e058fe2a27f05d8f1d3b98c78403937c18` |

## 12. Closure implications and disposition

1. Retain the structural 18-plane gate, but add independent contract-conformance and call-graph/integration evidence; do not use path presence as semantic closure.
2. Unify agent selection, assignment, qualification, parent-child lineage, scheduling and result aggregation.
3. Make claim/evidence lineage canonical across NEXUS, HYPERSYNTH, agents, FINCH, MIRROR WORLD, cyber range and domain packages.
4. Keep simulation, forecasts and source observations as distinct epistemic classes; define calibrated acceptance only for explicit domains and scopes.
5. Unify provider retries and all external effects under a single attempt/effect lifecycle.
6. Distinguish dispatch acceptance receipts from authenticated provider receipts, observed effects and verified commits.
7. Extend browser source checks with separately specified runtime enforcement and release evidence.
8. Connect signed manifests to trusted builds, dependency provenance, approval, deployment and rollback.

No ADR is accepted or closed by this pass. No tests were executed in this pass. No integration, merge, deployment or architecture freeze is authorized. W01–W12 remain PARTIAL.
