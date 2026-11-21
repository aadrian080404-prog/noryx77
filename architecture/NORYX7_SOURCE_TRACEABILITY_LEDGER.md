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
