# NORYX7 — Repository Source Traceability Ledger

**Status:** architecture inventory based on repository tree inspection; file presence is not implementation or verification evidence  
**Repository:** `aadrian080404-prog/noryx77`  
**Inspected base:** `main` at `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Purpose:** map the source tree to canonical architecture planes and future integration/verification work without changing runtime code.

## 1. Evidence rules

- **Present:** path exists in the inspected repository tree.
- **Documented:** an architecture document describes the boundary or intended behavior.
- **Partial/unknown:** the tree alone cannot establish completeness, runtime correctness, or production readiness.
- **Verified:** reserved for exact test/CI evidence tied to a commit and stated scope; this ledger does not assign this status.

A file can support multiple planes. The primary mapping below is organizational, not an exclusive ownership claim.

## 2. Canonical source-to-plane map

| Plane | Primary source paths observed | Architecture references | Inventory note |
|---|---|---|---|
| P01 Ingress | `core/contracts.py`, `core/limits.py`, `core/platform.py`, `core/multimodal.py`, `core/voice.py`, `core/http_provider.py` | Complete System Blueprint; Canonical Plane Contracts | Request schemas and modality/provider intake are spread across core and surface adapters. |
| P02 Understanding | `core/user_understanding.py`, `core/interaction_context.py`, `jarvis/context/authorized.py`, `jarvis/interaction/session.py` | User Understanding Fabric; Surface/Runtime/Distribution | Consent and interaction metadata must remain non-authoritative. |
| P03 Cognition | `core/hypersynth.py`, `core/hypersynth_runtime.py`, `core/reasoning.py`, `core/metacognition.py`, `core/metacognitive_challenge.py`, `core/finch.py`, `core/personality.py` | HYPERSYNTH Kernel; Universal Intelligence Fabric | Multiple cognitive modules exist; stage ownership and shared lifecycle need reconciliation. |
| P04 Planning | `core/planning.py`, `core/decomposition.py`, `jarvis/core/decomposition.py` | HYPERSYNTH Kernel; JARVIS Architecture | Core and JARVIS have separate planning surfaces; adapter boundary must be explicit. |
| P05 Routing | `core/router.py`, `core/resource_router.py`, `core/provider_router.py`, `core/provider_execution.py`, `core/provider_resilience.py`, `noryx7_runtime/model_fabric.py` | Universal Intelligence Fabric; Real Runtime | Model/provider routing and compute placement are related but distinct routing decisions. |
| P06 Agents | `core/agent_core.py`, `core/agent_fabric.py`, `core/agent_identity.py`, `core/agent_mesh.py`, `core/agent_runtime.py`, `core/agent_skills.py`, `core/agents.py`, `core/collaboration.py`, `core/coordination.py`, `core/supervisor.py`, `core/operational_fabric.py` | HYPERSYNTH Kernel; Universal Intelligence Fabric | Agent identity, skills, dispatch and collaboration need one canonical lifecycle contract. |
| P07 Capabilities | `noryx7_runtime/capabilities.py`, `core/policy.py`, `core/authorization_replay.py`, `core/multiauth.py` | Real Runtime; Cryptographic Boundaries; Defense Matrix | Authority belongs to policy/capability boundaries, not agent skills or plans. |
| P08 Tools | `core/tools.py`, `core/tool_protocol.py`, `core/actions.py`, `noryx7_runtime/adapters.py`, `core/sandbox.py` | Real Runtime; PowerShell & Cloud Terminal Fabric | Tool registry, adapter protocol and sandbox contracts need explicit common result schema. |
| P09 Memory | `core/context.py`, `core/memory.py`, `core/memory_hierarchy.py`, `core/secure_memory.py`, `core/secure_storage.py`, `jarvis/memory/store.py` | Complete System Blueprint; Cross-Cutting Contracts | Context, working memory, durable memory and secure storage are distinct lifecycle layers. |
| P10 Runtime | `core/runtime.py`, `core/operational_runtime.py`, `core/execution_fabric.py`, `core/execution_trace.py`, `core/job_supervisor.py`, `noryx7_runtime/engine.py`, `noryx7_runtime/lifecycle.py`, `noryx7_runtime/scheduler.py` | Real Runtime; HYPERSYNTH Kernel | Multiple runtime/facade layers require explicit ownership and migration map before integration. |
| P11 Security | `core/security.py`, `core/security_integration.py`, `core/identity.py`, `core/crypto.py`, `core/secure_channel.py`, `core/key_lifecycle.py`, `core/trust_chain.py`, `core/perimeter.py`, `core/egress.py`, `core/secure_boot.py`, `core/attestation.py`, `core/authorization_replay.py`, `core/multiauth.py` | Cryptographic Boundaries; Defense Matrix | Identity, authentication, integrity, authorization and policy are separate concepts even where modules are adjacent. |
| P12 State | `core/state.py`, `core/state_journal.py`, `noryx7_runtime/state.py`, `noryx7_runtime/attestation.py` | Real Runtime; Cryptographic Boundaries | State proposal, journal, attestation and commit semantics require a canonical transaction lifecycle. |
| P13 Distribution | `core/distributed.py`, `core/device.py`, `core/device_fabric.py`, `core/offline.py`, `core/offline_adapters.py`, `core/offline_anchor.py`, `ecosystem/global_fabric.py`, `ecosystem/global_scale.py` | Edge Node Fabric; Real Runtime; Surface/Runtime/Distribution | Device, edge, cloud and offline are separate trust and availability profiles. |
| P14 Interfaces | `jarvis/` (assistant surface), `noryx-browser/` (Android browser), `core/voice.py`, `core/platform.py`, `core/jarvis_runtime_bridge.py` | Complete System Blueprint; JARVIS Architecture; Browser README | Browser v0.1 remains a separate product; future bridge is a new explicit contract. |
| P15 Audit | `core/audit.py`, `core/observability.py`, `core/alerting.py`, `core/evaluation.py`, `core/evaluation_campaign.py`, `core/execution_trace.py`, `jarvis/security/audit.py` | Defense Matrix; Real Runtime; Domain/Operational Assurance | Diagnostic telemetry and tamper-evident audit evidence must remain distinct. |
| P16 Recovery | `core/recovery.py`, `core/defense.py`, `noryx7_runtime/recovery.py`, `jarvis/core/recovery.py`, `ecosystem/isolation.py` | Defense Matrix; Real Runtime | Multiple recovery facades exist; canonical controller and trust-root bootstrap require explicit resolution. |
| P17 Performance | `core/limits.py`, `core/resource_router.py`, `core/provider_resilience.py`, `ecosystem/global_scale.py`, `tests/million/` | Universal Intelligence Fabric; Verification Scale | Existing load/evaluation assets do not by themselves establish SLOs or production capacity. |
| P18 Universal Intelligence | `core/universal_intelligence.py`, `core/subtask_uif.py`, `core/subtask_verification.py`, `core/frontier_capabilities.py`, `core/adversarial.py` | Universal Intelligence Fabric; Cross-Cutting Contracts; Domain/Operational Assurance | Domain assessments and subtask verification need explicit epistemic and source lineage contracts. |

## 3. Cross-cutting implementation locations

| Cross-cutting domain | Source paths observed | Architecture mapping |
|---|---|---|
| NEXUS prerequisites | `core/contracts.py`, `core/context.py`, `core/memory.py`, `core/universal_intelligence.py`, `core/reasoning.py`, `noryx7_runtime/contracts.py` | Existing typed contracts and evidence-bearing structures; not a complete semantic IR or wire protocol. |
| FRL prerequisites | `core/verification.py`, `core/subtask_verification.py`, `core/metacognitive_challenge.py` | Existing verification/challenge surfaces; no general formal proof assistant architecture is implied by these names. |
| MIRROR WORLD prerequisites | `core/cyber_range.py`, `core/sandbox.py`, `core/evaluation_campaign.py`, `core/adversarial.py` | Existing sandbox/cyber-range/evaluation components; not a complete digital twin or universal simulator. |
| Supply chain | `core/supply_chain.py`, `core/secure_boot.py` | Artifact/source trust and boot trust boundaries. |
| Self-improvement | `core/self_improvement.py` | Proposal and evaluation boundary; root policy/trust controls remain immutable to agents. |
| Business/project | `architecture/BUSINESS_PROJECT_FABRIC.md` | Architecture document; funds and transaction authority remain separate. |
| Cloud terminal | `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md` | Architecture document; no claim that every described shell/cloud capability exists. |
| Ecosystem/closure | `ecosystem/closure_contract.py`, `ecosystem/completeness.py`, `ecosystem/global_closure.py`, `ecosystem/structural_manifest.py`, `ecosystem/boundaries.py` | Structural and closure-control components; their exact gate semantics must be reconciled with the architecture freeze contract. |

## 4. Surface and package inventory

### JARVIS
Observed package families:
- `jarvis/agent`, `context`, `core`, `interaction`, `memory`, `observation`, `perception`, `providers`, `security`, `tools`;
- architecture/readme and dedicated tests under `jarvis/tests`.

### NORYX Browser
Observed Android application:
- Kotlin controllers and navigation policy/state;
- Android manifest, XML layouts/resources and Gradle configuration;
- debug-only TestLab and network security configuration;
- navigation unit tests and repository-level browser-isolation tests.

The Browser README explicitly defines a standalone WebView v0.1 with no AI, chatbot, HYPERSYNTH, cloud accounts, scraping, tracking or telemetry. Future integration is a separate design decision.

### Runtime
Observed package:
- contracts, engine, lifecycle, scheduler, adapters, capabilities, model fabric, attestation, state and recovery;
- dedicated tests for lifecycle, engine, adapters, capabilities, model fabric, replay, journal, recovery and continuity.

### Ecosystem
Observed package:
- boundaries, isolation, browser isolation, closure contract, completeness, dispatch contract, front runtime, global closure/fabric/scale, orchestration, runtime dispatch and structural manifest;
- tests for global fabric and repository-wide closure behaviors.

## 5. Existing test inventory anchors

The repository tree includes tests across:
- `core/test_*.py` for identity, authorization, security, crypto, memory, runtime, HYPERSYNTH, agents, tools, cyber range and recovery;
- `noryx7_runtime/test_*.py` for engine, lifecycle, capabilities, adapters, model fabric, attestation, state, replay and recovery;
- `jarvis/tests/` for runtime, boundaries and audit;
- `tests/` for ecosystem, orchestration, offline, closure, browser isolation, provider E2E, state/recovery and scale campaigns;
- `noryx-browser/app/src/test/` for navigation policy/input.

This is an inventory of test locations only. It does not state that any test was run in this architecture-only cycle.

## 6. Architecture risks exposed by the inventory

1. **Multiple runtime facades:** core runtime, operational runtime, HYPERSYNTH runtime, JARVIS runtime and noryx7_runtime need a single documented authority/lifecycle map.
2. **Multiple state and recovery surfaces:** core state/journal, runtime state/attestation, JARVIS state/recovery and ecosystem recovery/isolation need clear ownership and adapter direction.
3. **Agent subsystem breadth:** agent identity, skills, fabric, mesh, runtime, collaboration, coordination and supervision need one lifecycle and delegation model.
4. **Provider versus resource routing:** model/provider selection and node/compute placement must not be conflated.
5. **Security decomposition:** cryptographic integrity, identity, authentication, authorization, policy, capability, perimeter and egress must remain explicit separate boundaries.
6. **Browser bridge ambiguity:** Browser v0.1 remains standalone; future bridge contracts must not leak privileged APIs into WebView.
7. **Evidence/proof/simulation distinction:** evidence registry, FRL and MIRROR WORLD need explicit non-interchangeable result types.
8. **Closure-gate semantics:** architecture registry, ecosystem completeness, freeze contract and CI checks need one final gate definition.

## 7. Next use

This ledger becomes the source-to-contract traceability index for the architecture-freeze review. For every listed path, the next pass must determine:
- exact public contract and owner;
- whether it is canonical, adapter, facade, legacy or test-only;
- state and authority ownership;
- dependencies and duplicate responsibilities;
- implementation status supported by code inspection;
- required future verification and regression evidence.

No source module is declared complete by this inventory alone.


## Deep source anchors added (2026-11-22)

| Source path | Workstream(s) | Direct source role | Unresolved architecture question |
|---|---|---|---|
| `core/system_fabric.py` | W02, W04, W09 | Shared JARVIS/NORYX execution substrate and object-consistency boundary | Composition root versus coordinator versus dependency container |
| `core/execution_fabric.py` | W02, W05, W07 | Environment adapter observation/execute boundary with authorization callback | Relation to RuntimeEngine, ActionGate and MIRROR WORLD Reality Bridge |
| `noryx7_runtime/engine.py` | W02–W05 | Data-plane execution lifecycle, scheduler, signer, identity, replay and optional journal | Canonical execution engine or compatibility/data-plane adapter |
| `noryx7_runtime/state.py` | W03, W09 | Signed attestation journal and step reservation | In-memory versus durable reservation semantics and namespace |
| `noryx7_runtime/recovery.py` | W03, W09 | Journal recovery and identity/attestation validation | Coordination with core RecoveryController and ControlPlane |
| `core/recovery.py` / `core/control_plane.py` | W01, W03, W09, W11 | Recovery epoch, defense synchronization and artifact admission | One epoch authority and crash-consistent transition protocol |
| `core/offline_adapters.py` / `core/offline_anchor.py` | W08, W09 | Policy/verification/cipher adapters and monotonic snapshot marker | Production anti-rollback anchor, durable outbox and revocation freshness |
| `core/agent_mesh.py` / `core/agent_runtime.py` / `core/coordination.py` | W04 | Agent roles, liveness, assignment, execution and consensus | Relationship to native and operational agent fabrics |
| `core/device.py` / `core/egress.py` | W01, W05, W08, W09 | Device capability gate and explicit egress allowlist | Enforcement boundary and trust/epoch binding |
| `core/architecture_registry.py` | all planes | Structural plane contract completeness | Difference from evidence-backed architecture freeze gate |
| `.github/workflows/*.yml` | W11 | Seven CI workflow definitions | Release/deployment pipeline, production environment and DR ownership |


## Polyglot source anchors added (2026-11-22)

| Source path | Workstream(s) | Direct source role | Unresolved architecture question |
|---|---|---|---|
| `jarvis/core/runtime.py` | W01–W05, W09 | JARVIS composition of dual policy, workload identity, RuntimeEngine, SystemFabric, bridge, request state and audit | Single principal/policy authority and cross-store commit/recovery semantics |
| `core/jarvis_runtime_bridge.py` | W02–W05 | JARVIS plan translation to RuntimeEngine and core ToolExecutor/ActionGate | Exact scope, retry, idempotency and correlation boundary |
| `gateway/server.py` / `gateway/auth.py` | W01, W08, W09, W11 | HTTP boundary and HMAC bootstrap/session authority | Client-to-principal binding, TLS termination, multi-instance revocation and secret lifecycle |
| `gateway/runtime_adapter.py` | W02, W08 | Authenticated browser request adapter to OperationalNORYXRuntime | Client ID trust and tenant/session mapping |
| `services/jarvis-gateway-go/main.go` | W02, W08, W11 | Go health/digest service | Intended maturity and relationship to Python gateway |
| `services/jarvis-runtime-rs/src/lib.rs` | W02, W05 | Rust envelope canonical digest and deny helper | Wire compatibility and authentication/authorization ownership |
| `ios/NoryxIOSAdapter` | W01, W08, W09 | Local device/capability/epoch/replay adapter | Signed grants, durable replay, remote revocation and attestation |
| `android/noryx7-jarvis-bridge` | W08 | Audio wake PCM interface | Concrete permission/audio lifecycle and privacy policy |
| `noryx-browser/app/src/main` | W08, W09 | HTTPS navigation and gateway session client | Bootstrap secret provisioning, device binding, WebView threat model |
| `render.yaml` / `noryx7_operational.py` | W02, W11 | Hosted Python service and model-provider runtime configuration | Multi-artifact release, key injection, scale, backup and DR |


## W06–W12 parallel expansion source anchors — 2026-11-22

| Source path | Workstream(s) | Directly observed behavior | Contract gap / caution |
|---|---|---|---|
| `core/universal_intelligence.py` | W06, W10 | Evidence/DomainAssessment structures, deterministic keyword/risk routing, evidence-strength average, contradiction/uncertainty checks | Domain vocabulary is limited; confidence is not calibrated truth; no canonical cross-language ontology |
| `core/verification.py` | W06, W09 | Task/result/state shape and identity checks | Output-presence checks do not prove semantic correctness or domain validity |
| `core/cyber_range.py` | W07, W09 | Sandbox-only synthetic target, owner authorization and bounded symbolic phases | No evidence of general digital twin, real-world bridge or calibrated simulator |
| `core/sandbox.py` | W07, W09 | Fail-closed sandbox state machine and denied privileged profile flags | Actual OS/container/network isolation is external to this source abstraction |
| `core/evaluation_campaign.py` / `core/adversarial.py` | W07, W09, W11 | Deterministic generated scenarios, holdout selection and bounded campaign manifest | Holdout leakage governance, external validation and evidence independence remain open |
| `ecosystem/boundaries.py` | W06, W08, W12 | Four-front intent envelope with front, operation, payload digest and principal | Digest/ID construction is not authentication, authorization or complete NEXUS wire |
| `ecosystem/global_fabric.py` | W03, W08, W12 | In-memory memory metadata/replica IDs and identity/session/device/capability index | No durable distributed store, cryptographic authority or deletion/tombstone propagation established |
| `ecosystem/global_scale.py` | W05, W08, W11 | In-memory region/cell registries, capacity selection, bounded queue, budgets, degradation, metrics, DR and staged self-healing | Not a production cloud, durable broker, fleet telemetry or measured SLO implementation |
| `ecosystem/closure_contract.py` / `ecosystem/completeness.py` | W02, W08, W09, W11 | Four-front structural boundary contract and fail-closed structural gate | Structural completeness is not evidence-backed architecture freeze or runtime assurance |
| `ecosystem/runtime_dispatch.py` | W01, W02, W04, W08 | Principal authorization callback, front topology check and handler dispatch | Authorizer trust, durable idempotency, action-level capability and canonical ActionGate relation remain open |
| `gateway/server.py` / `gateway/auth.py` | W01, W08, W09, W11 | Bootstrap token and HMAC short-lived client session; bounded HTTP body | Client ID is not verified principal; secret custody, TLS termination and distributed revocation remain external |
| `ecosystem/global_scale.py` | W11, W12 | Usage/resource and regional control primitives | No commercial payment ledger, tenant billing, community governance or impact audit exists in these primitives |


## W01–W05 and shared cognitive substrate source anchors — 2026-11-22

| Source path | Workstream(s) | Directly observed behavior | Contract gap / caution |
|---|---|---|---|
| `core/contracts.py` | W02, W06 | TaskSpec/ActionSpec/AgentResult/VerificationResult typed records | Execution/task identity fields are distinct from JARVIS request/step identities |
| `core/hypersynth.py` | W02, W04, W05, W06 | End-to-end bounded cognitive pipeline, task binding, UIF routes, plan/hypothesis/simulation, agent allocation and ActionGate/tool path | Inspected assignment execution loop is sequential; lifecycle ownership and shared journal/dispatch transaction remain open |
| `core/reasoning.py` | W06, W07 | Hypothesis generation from plan steps; structural verification; bounded internal feasibility simulator | Not a domain-calibrated causal/physical simulator |
| `core/metacognition.py` | W06 | Stage/count/identity checks and pipeline-check ratio | Confidence is not calibrated truth probability |
| `core/universal_intelligence.py` | W06, W10 | Bounded specialist domain routing and evidence/risk/contradiction assessment | Routing vocabulary and evidence strength do not certify specialist competence or factual truth |
| `core/memory.py` | W03 | Bounded in-memory store, deep-copy isolation, execution filter and delete | No durable provenance/tenant/consent/retention/tombstone contract in this store |
| `core/memory_hierarchy.py` | W03 | Bounded L0–L5 key/value records and explicit promotion | Records lack source/consent/tenant/expiry/lineage metadata |
| `core/context.py` | W02, W03 | Versioned task context and optional prior memory hydration | Memory-list exceptions are treated as empty memory; requires explicit degraded-context state |
| `jarvis/memory/store.py` | W03, W08 | Separate bounded in-memory key/value store | No execution isolation, provenance, deep-copy, retention or deletion protocol |
| `jarvis/core/contracts.py` / `jarvis/core/orchestrator.py` | W01, W02, W04 | Request principal/request ID, immutable plan steps/dependencies, per-step policy authorization and ordered execution | Separate request lifecycle and policy semantics require explicit bridge contract |
| `jarvis/tools/registry.py` | W02, W04, W09 | Optional adapter from JARVIS capability registry to core ToolExecutor registry | Step reconstruction and result mapping need canonical schema/version and lifecycle owner |
| `jarvis/security/authorization.py` | W01, W09 | In-memory principal/capability/target grants | No issuer lineage, expiry, signed grant or durable revocation contract in this abstraction |
| `core/agent_mesh.py` | W04 | Role-based registry, deterministic first matching node | Selection is not health/capacity/authorization or independent consensus |
| `core/coordination.py` | W04, W02 | Bounded assignment, ActionGate execution, live identity recheck, output/result verification and equality consensus | Assignment is capped to max_agents; plan truncation/partial completion semantics must be explicit |
| `core/agent_fabric.py` | W01, W04 | Skill/identity/principal-gated bounded agent dispatch | Overlaps with coordinator/supervisor/operational fabric; precedence remains open |
| `core/agent_runtime.py` | W04, W11 | Agent lifecycle/heartbeat and live identity trust state | Heartbeat registry is local process state, not distributed fleet liveness |
| `core/operational_fabric.py` | W04 | Router/supervisor selection, dispatch and result admission | Overlapping dispatch owner; shared scheduler contract not established |
| `core/provider_router.py` | W05 | Deterministic capability selection and exception-based failover | Does not itself evaluate data residency, privacy, capacity, cost or semantic equivalence |
| `core/provider_execution.py` | W05, W09 | Provider handler adapted to ExecutionFabric with per-call authorizer callback | Current gateway resolution and retry semantics differ from ProviderRouter.execute |
| `core/resource_router.py` | W05, W11 | Tier choice from complexity/privacy/latency flags | No live capacity, region, cost, energy or queue telemetry in the selector |
| `core/multimodal.py` | W06, W08, W09 | Modality enum and digest/locator media references | Locator trust, encryption, consent, retention and safe resolution remain open |
| `core/self_improvement.py` | W07, W09, W11 | Proposal-only staged improvement and external admission boundary | Production release signer, reviewer authority, protected-zone inventory and rollback owner remain external/open |
| `core/offline.py` / `core/offline_anchor.py` | W03, W08, W09 | Authenticated snapshot callback, bounded encrypted queue, recovery guard and SQLite monotonic anchor adapter | Durable outbox, production hardware anchor and cross-store commit atomicity remain open |
| `core/supply_chain.py` | W09, W11 | Ed25519 signed artifact manifest and digest verification against trusted key set | Trusted key lifecycle, release approval, SBOM, reproducible build and deployment promotion remain separate |
| `core/observability.py` | W09, W11 | Bounded append-only in-memory security event buffer | Not durable centralized telemetry or an incident-response system |
| `ecosystem/front_runtime.py` / `ecosystem/runtime_dispatch.py` | W01, W02, W08 | Four-front dispatch adapters and principal authorization callback | One lifecycle owner, canonical principal mapping and cross-front transaction semantics remain open |
| `ecosystem/global_closure.py` | W02, W09, W11 | Structural import/symbol/path/browser isolation gate | Structural closure does not establish operational readiness, source coverage or comprehensive assurance |
| `core/architecture_gate.py` / `core/architecture_registry.py` | All | 18-plane canonical structural contracts and required acceptance metadata | Registry completeness is not evidence-backed architecture freeze |
| `architecture/COMPLETE_SYSTEM_BLUEPRINT.md` | All | Four-front model, pipeline, memory, domain, business, recovery, security and verification-after-architecture direction | Source-of-truth status/version precedence relative to newer ADRs must be explicit |


## Runtime, model and repository inventory anchors — 2026-11-22

| Source path | Workstream(s) | Directly observed behavior | Contract gap / caution |
|---|---|---|---|
| `noryx7_runtime/contracts.py` / `lifecycle.py` | W02 | Intent, execution context, action envelope and terminal lifecycle values | No indeterminate/partial/compensation state in current enum |
| `noryx7_runtime/scheduler.py` | W02, W04, W05 | Deterministic topological ordering and cycle/missing-dependency rejection | Scheduler returns an order; it does not itself execute steps concurrently |
| `noryx7_runtime/engine.py` | W01–W05, W09 | Pre-dispatch authorization/replay checks, optional reservation, adapter dispatch, output verification, attestation and commit callback | Post-dispatch committer failure returns FAILED while reservation is retained; outcome may be externally indeterminate |
| `noryx7_runtime/model_fabric.py` | W05, W06, W09, W11 | Capability/cost/latency candidate selection, bounded fan-out, request/result digest and optional keyed HMAC | Keyed MAC and runtime binding are optional; unkeyed result_mac is deterministic digest only |
| `noryx7_runtime/model_adapters/openrouter.py` | W05, W08, W11 | Non-streaming text provider adapter with timeout and API key | Tools unsupported in current string-only adapter; cost/latency values are static metadata |
| `web/app.py` | W01, W02, W08, W09 | /v1/session and /v1/execute use gateway session path; /api/chat invokes operational runtime directly | Route-level authentication equivalence/upstream enforcement not established by this file |
| `devtools/test_lab/runner.py` | W11 | Fixed allowlist for compile, pytest, closure and completeness commands | Tool presence does not imply execution or successful evidence |
| `devtools/audit_next_architecture_phase.py` | W02, W11 | AST inventory of configured directories, imports, classes and functions | No dynamic call graph or whole-repository semantic completeness |
| `devtools/consolidate_architecture_phase.py` | W02, W11 | Expected-path and keyword-based capability resolution | Keyword/path resolution is not proof of runtime ownership or capability completeness |
| `.github/workflows/*.yml` | W08, W11 | Seven workflows cover Python, Go, Rust and Android Browser build/test paths | Dedicated iOS workflow not found in this inventory; automatic PR workflows are separate from architecture closure |
| `render.yaml` / `web/app.py` | W08, W11 | One Python web service/runtime entrypoint and web/API routes | Does not define release topology for all polyglot/mobile artifacts |

## Additional source mapping — 2026-11-22 ingress/observation/global-scale pass

| Source path | Architectural responsibility | Workstreams | Reconciliation status / limitation |
|---|---|---|---|
| `web/app.py` | FastAPI ingress, direct chat and gateway API routes | W01/W02/W08/W09 | MAPPED; direct `/api/chat` differs from session-authenticated `/v1/execute`; upstream controls not established |
| `gateway/auth.py` | Bootstrap exchange and HMAC session tokens | W01/W09 | MAPPED; stateless token expiry/integrity, no visible durable revocation registry or client attestation |
| `gateway/server.py`, `gateway/runtime_adapter.py` | Authenticated gateway execution and request-to-task translation | W02/W08 | MAPPED; client ID is a label until resolved to a verified principal |
| `core/llm/agent.py` | Model-backed primary/secondary reasoning agents | W04/W05/W06 | MAPPED; capability labels do not prove adapter availability or authorize actions |
| `core/llm/model_fabric_bridge.py` | Single-model text generation bridge | W05/W06 | MAPPED; tools empty, no action authority |
| `core/llm/self_knowledge.py` | Bounded system context for reasoning agents | W06 | MAPPED; not a signed/versioned manifest |
| `jarvis/providers/base.py` | Minimal provider protocol | W05/W11 | MAPPED; lacks operational, privacy, usage, cancellation and structured tool contract |
| `jarvis/context/authorized.py` | Callback-gated context acquisition | W01/W06/W08 | MAPPED; no field-level scope, tenant, consent receipt or source attestation |
| `jarvis/observation/fabric.py` | Callback-gated observation wrapper | W01/W06/W08 | MAPPED; caller-supplied timestamp and descriptive provenance are not authenticated evidence |
| `jarvis/perception/audio.py` | Audio frame and clap wake-pattern event | W08/W09 | MAPPED; wake event is not identity, permission or authorization |
| `core/user_understanding.py` | Consent enum and heuristic profile extraction | W01/W06/W12 | MAPPED; confidence is heuristic; durable consent, correction/deletion and lineage remain open |
| `core/cyber_range.py` | Synthetic-only symbolic cyber simulation | W06/W07/W09 | MAPPED; local owner record is not cryptographic authorization for Reality Bridge |
| `core/device_fabric.py` | In-memory device capability registry | W05/W08/W09 | MAPPED; first online match, no attestation/lease/residency selection |
| `core/distributed.py` | Node and shard placement descriptors | W03/W08/W09 | MAPPED; encrypted flag does not establish key custody, replication or consistency |
| `ecosystem/global_scale.py` | Region/cell registry, capacity accounting, event queue and language envelope | W05/W08/W11 | MAPPED; in-memory primitives, no durable broker or atomic fleet reservation |

All entries are source anchors only. They do not establish production deployment, trust assurance or acceptance of the corresponding ADRs.

## Additional source mapping — 2026-11-23 assurance/offline/semantic pass

| Source path | Architectural responsibility | Workstreams | Reconciliation status / limitation |
|---|---|---|---|
| `core/observability.py` | Bounded security event buffer | W09/W11 | MAPPED; in-memory local sequence, no durable authenticated telemetry or incident ownership |
| `core/egress.py` | Component/host/port/protocol allowlist | W08/W09/W11 | MAPPED; local policy primitive, not proof of socket/DNS/redirect/proxy enforcement |
| `core/supply_chain.py` | Ed25519 signed artifact manifest and digest verifier | W08/W09/W11 | MAPPED; trusted-key set provisioning, SBOM/build provenance/release approval/promotion remain open |
| `core/self_improvement.py` | Proposal-stage state machine | W09/W11 | MAPPED; external admission is an abstract method boundary, no independent signer/reviewer or rollback |
| `core/offline.py` | Snapshot, offline execution and encrypted sync queue | W03/W08/W09 | MAPPED; digest is not signature, queue is in-memory, durable outbox and uncertain outcome semantics open |
| `core/offline_anchor.py` | SQLite monotonic snapshot marker | W03/W09 | MAPPED; source warns production protected storage/TPM/HSM needed |
| `core/verification.py` | Structural task/result/output checks | W06/W10 | MAPPED; output presence is not semantic truth or domain correctness |
| `core/reasoning.py` | Plan-derived hypotheses and bounded feasibility preflight | W06/W07 | MAPPED; simulator checks structure/non-empty statement, not calibrated physical/domain feasibility |
| `core/metacognition.py` | Pipeline identity/count checks and challenge verification | W06 | MAPPED; confidence is ratio of passed checks, not calibrated truth probability |
| `core/universal_intelligence.py` | Keyword/risk/length specialist routing and assessment contracts | W06/W10 | MAPPED; route labels do not certify specialist competence; assessment scores are not calibrated by shape validation |
| `core/architecture_gate.py` | 18-plane structural contract/path-existence gate | W01/W02/W11 | MAPPED; existence/fields do not prove callers, semantics, deployment or evidence-backed freeze |
| `core/architecture_registry.py` | Canonical plane definitions | W01/W02 | MAPPED; structural definitions need source/call-site and deployment evidence |
| `core/device.py` | Device trust/capability gate and adapter boundary | W01/W08/W09 | MAPPED; local grant state and epoch; enrollment, signed grants and remote revocation remain open |
| `ecosystem/front_runtime.py`, `ecosystem/runtime_dispatch.py` | Cross-front principal-gated dispatch wrapper | W01/W02/W08 | MAPPED; callback authorization and receipt semantics do not settle canonical lifecycle/cross-store transaction ownership |

Source presence is not implementation acceptance or production assurance.

## Additional source mapping — 2026-11-23 four-front/memory/ecosystem pass

| Source path | Architectural responsibility | Workstreams | Reconciliation status / limitation |
|---|---|---|---|
| `ecosystem/boundaries.py` | Four-front intent envelope and deterministic ID | W01/W02/W08 | MAPPED; default principal label is front name, not authenticated identity |
| `ecosystem/runtime_dispatch.py` | Principal callback, topology check and handler dispatch receipt | W01/W02/W08 | MAPPED; injected authorizer root external, receipt not inherently durable/signed, lifecycle outcome is coarse |
| `ecosystem/front_runtime.py` | JARVIS/HYPERSYNTH front adapters | W02/W08 | MAPPED; thin wrappers do not settle canonical lifecycle/state transaction owner |
| `ecosystem/closure_contract.py` | Required front boundaries/invariants | W02/W08 | MAPPED; validates structure, not invocation coverage |
| `ecosystem/structural_manifest.py` | Required source paths per front | W02/W08 | MAPPED; path existence is not behavior or complete call graph |
| `ecosystem/global_fabric.py` | L0–L5 memory metadata and session authorization index | W01/W03/W06/W09/W12 | MAPPED; in-memory metadata/index, no durable content, verified replica or issuer/revocation root |
| `architecture/BUSINESS_PROJECT_FABRIC.md` | Business/project lifecycle, commissions and funds separation | W09/W12 | ARCHITECTURE INTENT; inspected ecosystem package has no dedicated payment/ledger/marketplace implementation modules |
| `architecture/USER_UNDERSTANDING_FABRIC.md` | Consent-bound personalization and non-authority boundary | W01/W06/W12 | ARCHITECTURE INTENT; durable consent, correction and deletion lifecycle still open |
| `architecture/EDGE_NODE_ZIMABOARD_FABRIC.md` | Vendor-independent edge-node role | W05/W08/W09/W11 | ARCHITECTURE INTENT; device trust, egress and fleet enforcement remain separately open |

The absence of named product modules is limited to the inspected `ecosystem/` directory inventory; no global repository absence claim is made.


## Additional source mapping — 2026-11-24 agent dispatch/runtime pass

| Source path | Architectural responsibility | Workstreams | Reconciliation status / limitation |
|---|---|---|---|
| `core/agent_fabric.py` | Native AgentCore binding, skill registry, identity trust and principal callback | W01/W04/W09 | MAPPED; first eligible candidate runs; callback issuer/revocation/audit lineage external |
| `core/operational_fabric.py` | AgentSupervisor-backed selection, dispatch and AgentResult admission | W02/W04/W06 | MAPPED; local result admission, not durable commit or semantic truth proof |
| `core/supervisor.py` | Task verification, selected-agent identity and output/result admission | W04/W06/W09 | MAPPED; no durable lifecycle or domain-specific truth contract |
| `core/coordination.py` | Bounded assignments, ActionGate execution, identity recheck and equality consensus | W04/W06/W09/W10 | MAPPED; plan truncated to max_agents; equality consensus not universal for probabilistic/multimodal outputs |
| `core/agent_mesh.py` | Deterministic role lookup | W04/W05 | MAPPED; no identity/capability/liveness/capacity enforcement in this class |
| `core/agent_runtime.py` | Local agent status and heartbeat snapshots | W04/W08/W11 | MAPPED; not distributed signed heartbeat, lease or failure detector |
| `noryx7_runtime/scheduler.py` | Deterministic topological ordering | W02/W04/W05 | MAPPED; no concurrent execution |
| `noryx7_runtime/engine.py` | Sequential action dispatch, optional pre-dispatch reservation, verification, attestation and commit | W02/W03/W05/W09/W11 | MAPPED; post-dispatch failures can leave external effect uncertain; no INDETERMINATE lifecycle status |
| `noryx7_runtime/contracts.py`, `lifecycle.py` | Execution identity/status contract | W02/W03 | MAPPED; current status vocabulary lacks partial/indeterminate/reconciliation/compensation states |
| `core/architecture_gate.py`, `core/architecture_registry.py` | 18-plane structural field/path gate and definitions | W01/W02/W11 | MAPPED; all filename tokens exist in tree, but no semantic/call-site/deployment/freeze evidence |

Source snapshot: main `7d900bc75843ea968aa5886d251dbfac83a5d93c`. Source presence is not implementation acceptance or production assurance.


## Additional source mapping — cognitive/evidence/global-scale pass — 2026-11-24

| Source path | Architectural responsibility | Workstreams | Reconciliation status / limitation |
|---|---|---|---|
| `core/hypersynth.py` | Bounded cognition, decomposition, specialist routing, planning, hypothesis/simulation, sequential execution and result admission | W02/W04/W05/W06/W10 | MAPPED; max_agents bounds plan size and execution is sequential; structural simulation checks do not establish domain truth |
| `core/hypersynth_runtime.py` | Local composition root for policy, recovery, ActionGate, ToolExecutor, memory, collaboration and kernel | W01/W02/W03/W09/W11 | MAPPED; local composition, not distributed/durable atomicity |
| `core/collaboration.py` | Primary proposal → secondary critique → primary reconciliation | W04/W06/W09 | MAPPED; shared model/provider/evidence lineage may defeat independence; digests prove integrity, not truth |
| `core/metacognitive_challenge.py` | Challenge schema, injected independent verifier, structural pipeline challenge and adaptive scoring | W06/W10 | MAPPED; external verifier/dataset independence and score calibration unresolved |
| `core/evaluation.py`, `core/evaluation_campaign.py` | Dimension aggregation and deterministic synthetic/holdout manifest | W06/W10/W11 | MAPPED; no execution, evaluator authentication, result uniqueness or durable signed manifest |
| `core/finch.py` | Bounded event graph, keyword/severity relevance, batch anomaly and severity-mean forecast | W06/W07/W10 | MAPPED; heuristic only, no temporal calibration/backtest/causal validity |
| `core/multimodal.py` | Modality references and payload digest | W03/W06/W08/W09 | MAPPED; no payload encryption, locator authentication, consent or retention lifecycle |
| `core/distributed.py` | Local node/shard descriptors | W05/W08/W11 | MAPPED; no network replication, membership consensus, durability or failover |
| `ecosystem/global_scale.py` | Region/cell selection, capacity accounting, in-memory event queue and degradation primitives | W02/W05/W08/W11 | MAPPED; production adapters, durable broker, autoscaling, leases and telemetry absent from this module |
| `core/frontier_capabilities.py` | HTTPS research and external provider capability adapters; bounded chess analysis | W06/W09/W10/W12 | MAPPED; egress SSRF controls, source trust, provider attestation and regulated transaction lifecycle unresolved |
| `core/orchestration.py`, `ecosystem/completeness.py` | Request-stage state machine and structural completeness gate | W01/W02/W08/W11 | MAPPED; state transition/structural pass does not prove external execution or operational readiness |

Source snapshot: main `7d900bc75843ea968aa5886d251dbfac83a5d93c`. This is source-level architecture mapping, not a test or deployment claim.


## Additional source traceability — 2026-11-24

| Source path / scope | Observed responsibility | Evidence boundary / unresolved architecture |
|---|---|---|
| `core/verification.py` | Task/output/result shape, identity, cardinality, status and verification-marker checks | Structural acceptance is not semantic truth, entailment, source authority or domain validation |
| `core/reasoning.py` | Plan-derived hypotheses; identity/basis checks; structural feasibility simulator | No physical/domain calibration, causal validation, independent holdout or uncertainty model shown |
| `core/universal_intelligence.py` | Deterministic keyword/risk-based domain/strategy/budget routing and supplied assessment aggregation | Route is not competence or authority; supplied evidence-strength values are not calibrated by this component |
| `core/subtask_uif.py` | Bounded per-subtask routing with explicit `route_authority=False` | Does not qualify specialist agent or authorize actions |
| `core/subtask_verification.py` | Exact subtask result coverage/order and agent-result verification marker | Boolean evidence record and result marker do not establish source truth or semantic correctness |
| `core/frontier_capabilities.py` | HTTPS research fetch/search parsing and generic external provider adapter | DNS/IP/redirect, source authority, content isolation, authenticated provider receipts and transaction reconciliation remain open |
| `core/finch.py` | Event relevance/anomaly/forecast heuristics based on supplied severity, keywords and batch statistics | No calibrated temporal forecast or causal model established |
| `core/evaluation_campaign.py` | Synthetic scenario and holdout manifest generation | Does not by itself execute campaigns, authenticate evaluator, prove independence or establish statistical power |
| `ecosystem/` directory inventory | Front/runtime/global-fabric/global-scale/closure primitives | No dedicated financial ledger, marketplace, remediation measurement or community governance engine appeared in this inspected directory; repository-wide absence not asserted |
| `architecture/NORYX7_DOMAIN_OPERATIONAL_ASSURANCE.md` | Domain manifest and D01–D13 architecture catalog | Specification only; not proof of domain implementations, qualified experts or operational certification |
| `architecture/BUSINESS_PROJECT_FABRIC.md` | Commercial workflow, fund separation and transaction governance intent | Must be traced to actual ledgers/payment adapters, beneficial ownership, dispute and reconciliation paths |
| `architecture/USER_UNDERSTANDING_FABRIC.md` | Consent-bound personalization and sensitive-trait exclusions | Durable consent, source lineage, correction, deletion and profile-poisoning controls remain to be evidenced |

Source snapshot for this pass: branch `architecture/system-wide-closure-mirror-world-2026-11-21`, head observed at start `a36044b76db9e4a86c3a5a2cc195cde7b46e4a6e`. This table records inspected paths only; it is not an exhaustive call-site inventory.


## Additional ingress, memory, offline and operational source traceability — 2026-11-24

| Source path | Observed responsibility | Boundary / unresolved issue |
|---|---|---|
| `gateway/auth.py` | HMAC-SHA256 short-lived token with client_id, expiry and nonce | Shared bootstrap bearer; no server-side revocation, audience/scope, enrolled principal/device binding or nonce consumption shown |
| `gateway/server.py` | HTTP health/session/execute routes; bounded request body; TLS expected externally | No in-process TLS; production proxy trust/rate limits/CSRF/origin controls and session revocation remain external/unresolved |
| `gateway/runtime_adapter.py` | Maps client_id into task constraints and invokes OperationalNORYXRuntime | client_id is not resolved to an authenticated principal/device in this adapter |
| `noryx7_operational.py` | OpenRouter ModelFabric composition root and optional state-journal path | One configured model adapter; durable journal only if path configured; no polyglot service composition implied |
| `core/memory.py` | Bounded in-memory MemoryStore with deep-copy isolation and optional execution filter | Tenant/consent/provenance/expiry/tombstones/durable replicas absent from this store |
| `core/memory_hierarchy.py` | Bounded L0–L5 key/value hierarchy and promotion | No tenant, source, execution, consent, provenance, expiry or deletion metadata |
| `core/context.py` | Builds versioned snapshots and hydrates prior memory | `_memory_values` calls `list()` without execution filter; catches errors as empty tuple without degraded-state signal |
| `core/offline.py` | Authenticated snapshot callback, policy/recovery admission, encrypted bounded outbox abstraction and sync state | Queue is in-memory; exception path acknowledges/removes pending envelope even where external effect may be uncertain |
| `core/offline_anchor.py` | SQLite WAL/FULL monotonic snapshot marker | Documentation requires protected storage/TPM/HSM replacement or protection for production |
| `core/state_journal.py` | SQLite WAL/FULL append-only state commit journal, sequence and digest verification | Digest stored in same DB is not independent signed root; cross-store/external side-effect atomicity unresolved |
| `core/recovery.py` | In-process state/epoch machine and serialized `run_if_normal` critical section | Does not coordinate separate processes/nodes/databases or external transactions |
| `core/egress.py` | In-memory component/host/port/protocol allowlist | No DNS resolution pinning, redirect validation or proof every socket path is mediated |
| `core/provider_router.py` | First-match capability routing and generic exception failover | No typed uncertainty/retry safety; failover may be unsafe after an indeterminate side effect |
| `core/provider_execution.py` | Injected per-call authorizer and ExecutionFabric provider bridge | Action ID is deterministic from principal/provider/capability; no unique attempt receipt/idempotency lifecycle here |
| `core/resource_router.py` | Static DEVICE/EDGE/CLOUD selection by complexity/privacy/latency | No live capacity, residency, cost, energy or health telemetry |
| `core/supply_chain.py` | Ed25519 trusted-key manifest verification and artifact digest check | SBOM, build provenance, signer role/rotation/revocation, approval and staged rollback are separate |
| `core/self_improvement.py` | In-process proposal stage sequence and external admission boundary | Independent reviewer/signer, protected release zone and rollback evidence not supplied by this class |
| `core/observability.py` | Bounded in-memory security event buffer | Not durable/tamper-evident incident ledger; alert ownership/containment absent |
| `ecosystem/global_fabric.py` | Memory metadata index with payload/provenance digests and replica labels; local identity/session authorization index | Replica labels do not prove healthy independent replicas; no issuer/revocation authority or payload store |
| `ecosystem/runtime_dispatch.py` | Injected principal authorization and cross-front handler dispatch with receipt | Receipt is coarse; no durable idempotency ledger or domain result admission in this function |
| `ecosystem/front_runtime.py` | Thin HYPERSYNTH/JARVIS adapters | Does not establish one lifecycle owner or cross-store transaction |
| `render.yaml` | Single Python Uvicorn service with external secret injection | Does not deploy inspected Go/Rust/mobile surfaces as one integrated topology |
| `services/jarvis-gateway-go/main.go` | Go health and SHA-256 digest endpoints | Not full authenticated JARVIS runtime in inspected source |
| `services/jarvis-runtime-rs/src/lib.rs` | Rust envelope digest and deny-by-default helper | Not full identity/signature/dispatch/journal/recovery runtime in inspected source |

This ledger records bounded path-level observations, not a full call-site or deployment proof.


## Structural gate, secure memory, audit and platform assurance source traceability — 2026-11-24

| Source path | Observed responsibility | Boundary / unresolved issue |
|---|---|---|
| `core/architecture_registry.py` | Defines 18 canonical planes and ten non-empty descriptive fields per plane | Descriptive strings do not prove that integrations, trust boundaries, budgets or recovery are enforced |
| `core/architecture_gate.py` | Checks enum coverage, non-empty fields and existence of filename tokens in implementation boundary | Does not trace call sites, constructors, runtime reachability, integration, trust enforcement, tests or deployment |
| `core/secure_storage.py` | Authenticated-encryption record abstraction with namespace/record AAD and ciphertext snapshots | Inspected backing map is process-local memory; no durable database/replication/key lifecycle |
| `core/secure_memory.py` | Serializes MemoryItem and uses encrypted record adapter; optional execution-ID filter | Schema lacks tenant/principal, consent/purpose, provenance artifact, expiry/retention/tombstone and replica metadata |
| `core/audit.py` | In-memory SHA-256 event chain and HMAC-SHA256 checkpoint create/verify | Checkpoint not externally persisted by this class; no durable event ledger/trusted timestamp/independent signer |
| `core/agent_skills.py` | Local skill registry and descriptions | Registration is not qualification, version approval, jurisdiction or action authority |
| `core/platform.py` | Typed platform request/action; DeviceRuntimeBoundary and epoch gate | Platform adapter enrollment/attestation/revocation remain external |
| `ios/NoryxIOSAdapter/.../NoryxIOSPlatformAdapter.swift` | Actor-local grants, handlers, expiry, epoch and bounded consumed-action set | No signed grants, durable replay state, hardware attestation or remote revocation shown |
| `android/noryx7-jarvis-bridge/.../AudioWakeBridge.kt` | Narrow audio wake callback | Wake detection is not identity, explicit user intent, OS permission proof or ActionGate approval |
| `ecosystem/browser_isolation.py` | Static source marker scan for forbidden Browser integrations | Does not prove runtime behavior, dynamic dependencies, network destination or OS sandbox security |
| `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md` | Terminal/Cloud Shell target architecture and security requirements | No dedicated terminal runtime path found in the inspected recursive tree snapshot |

This ledger records the inspected snapshot and path-level findings; it is not a production security assessment.


## Agent execution, evidence, MIRROR WORLD and impact source traceability — 2026-11-24

| Source path | Observed responsibility | Boundary / unresolved issue |
|---|---|---|
| `core/agent_core.py` | Agent phase lifecycle, bounded sequential plan execution, optional authorization hook and verified response gate | Per-agent lock/local lifecycle; no durable attempt, lease, cancellation or distributed recovery in this class |
| `core/agent_fabric.py` | Agent identity/skill binding, principal context anti-spoofing and injected principal authorization | Principal is a label parameter; deterministic first authorized candidate; skill presence is not qualification |
| `core/agent_mesh.py` | Role registry and deterministic role routing | No identity registry or authorization boundary in this class |
| `core/coordination.py` | ActionGate-protected agent assignment, child task verification and result admission | Assignment truncates to `max_agents`; does not define complete DAG scheduling; equal output does not prove independent consensus |
| `core/operational_fabric.py` | Supervisor selection, dispatch, admission and optional audit calls | One-task wrapper; durable distributed leases/retry/cancel/recovery not established |
| `core/agent_runtime.py` | Local agent heartbeat/status with injected monotonic clock | Not distributed liveness or remote attestation |
| `core/verification.py` | Contract, identity, cardinality, completion and output-presence checks | Non-empty output and verification marker do not establish semantic truth or source entailment |
| `core/reasoning.py` | Plan-derived hypotheses and bounded structural feasibility checks | Not domain-calibrated simulation or causal/physical validation |
| `core/subtask_uif.py` | Bounded specialist routing with explicit `route_authority=False` | Routing label does not qualify specialist competence or grant authority |
| `core/subtask_verification.py` | Exact subtask result coverage/order and commit eligibility marker | String output + boolean verified marker is not source-anchored evidence |
| `core/universal_intelligence.py` | Domain route/assessment/evidence-shaped records and bounded confidence/uncertainty fields | Supplied strength/confidence are not source-authenticated or calibrated by shape checks |
| `core/evaluation_campaign.py` | Deterministic local adversarial case/holdout manifest and dimension-completeness approval | Does not itself generate independent evaluation evidence or prove campaign execution/pass |
| `core/finch.py` | Bounded event graph, relevance/anomaly and forecast-shaped records | Likelihood/horizon/evidence IDs do not establish calibrated predictive performance |
| `ecosystem/global_fabric.py` | L0–L5 memory metadata, payload/provenance digests and replica labels; local identity authorization index | In-process metadata map; no payload custody, healthy replica proof, issuer or cross-region consensus |
| `architecture/NORYX7_MIRROR_WORLD_ARCHITECTURE.md` | World graph, experiment manifest, simulation kernels, synthetic browser/cyber range and Reality Bridge target | Model calibration, independent validation, OOD validity and real-world actuation boundary remain evidence requirements |
| `architecture/BUSINESS_PROJECT_FABRIC.md` | Project lifecycle, financial boundary, commission/accounting workflow requirements | Does not establish deployed payment rails, double-entry ledger, settlement or disputes |
| `architecture/NORYX7_FOUR_FRONT_GLOBAL_MEMORY_AND_ECOSYSTEM_GOVERNANCE.md` | Global memory and identity governance requirements; marketplace/community/impact target architecture | Source inventory remains bounded; durable services and independent outcome accounting not established |

This is a source-snapshot traceability record, not an implementation or production-readiness certification.


## Tool protocol, provider and external-effect source traceability — 2026-11-24

| Source path | Observed responsibility | Boundary / unresolved issue |
|---|---|---|
| `core/tool_protocol.py` | Local ToolSpec/ToolResult registry; injected authorization callback; tool@version provenance | Callback sees ToolSpec only; no principal/session/target/attempt binding or immutable artifact/input/output provenance |
| `core/provider_resilience.py` | Bounded provider failover through ProviderRouter and ExecutionFabric; policy denial terminal | Generic exceptions trigger failover; deterministic attempt ID lacks caller operation/idempotency key; no remote effect certainty/receipt |
| `core/http_provider.py` | HTTPS-by-default JSON POST, timeout, response-size bound, secret environment lookup, redirects rejected | No DNS pinning/socket mediation/private-IP policy or remote idempotency/effect reconciliation proof |
| `core/execution_trace.py` | Per-execution in-memory SHA-256 hash chain with local verification | No durable persistence, external trusted head, signer identity, trusted time or event completeness guarantee |
| `core/egress.py` | In-memory component/host/port/protocol allowlist | Does not itself prove DNS rebinding resistance, redirect/socket enforcement or all-transport mediation |
| `core/secure_channel.py` | Authenticated channel framing, identity/session binding and bounded replay window | Channel integrity is not semantic action authorization or durable remote-effect receipt |
| `core/provider_router.py` | Capability-based provider registration/resolution | Selection is not provider qualification, residency/cost equivalence or retry safety |
| `core/provider_execution.py` | Injected authorization before provider adapter dispatch | Needs common operation/idempotency ID, durable attempt and receipt/reconciliation contract |
| `core/offline.py` | Offline envelope/queue and recovery integration | Queue durability and uncertain effect state must converge with provider dispatch lifecycle |

These are bounded source findings, not an end-to-end egress or provider security assessment.
