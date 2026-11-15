# NORYX7 — Architecture-to-Code Traceability Matrix

**Snapshot:** 2026-11-15  
**Baseline inspected:** `main` tree (507 entries; recursive Git tree not truncated), plus changed-file lists for the cited open PRs.  
**Status vocabulary:** BASELINE = path exists on main; PR-ONLY = implementation appears in an open PR branch, not confirmed in main; SPEC = defined in architecture docs; GAP = no authoritative implementation path confirmed by this inventory.

This is a path-level traceability map. Existence of a source or test file does not prove that the feature is complete or correct.

## Cognitive OS and execution core

| Domain | Main baseline paths | PR-only additions / related PRs | Required verification |
|---|---|---|---|
| HYPERSYNTH kernel | `core/hypersynth.py`, `core/hypersynth_runtime.py`, `core/decomposition.py`, `core/planning.py`, `core/reasoning.py`, `core/metacognition.py` | sandbox/runtime injection #62/#68/#71 | stage contracts, graph immutability, budgets, uncertainty, offline and end-to-end task flows |
| Task/context understanding | `core/context.py`, `core/interaction_context.py`, `core/user_understanding.py`, `core/subtask_uif.py`, `core/subtask_verification.py` | #16 plan binding | session isolation, provenance, ambiguity handling, plan-digest authorization |
| Agent Fabric | `core/agent_fabric.py`, `core/agent_identity.py`, `core/agent_runtime.py`, `core/agent_mesh.py`, `core/collaboration.py` | durable identity #46; atomic dispatch #48; collaboration identity #64/#71 | revocation race, delegated capability attenuation, identity epoch on every turn |
| Model Fabric | `noryx7_runtime/model_fabric.py`, `noryx7_runtime/model_adapters/openrouter.py`, `core/llm/agent.py`, `core/llm/model_fabric_bridge.py`, `core/provider_router.py`, `core/provider_resilience.py` | no new provider PR in current 65-PR inventory | provider fallback, response bounds, usage metering, no model authority, offline fallback |
| Canonical runtime | `core/runtime.py`, `core/operational_runtime.py`, `noryx7_runtime/engine.py`, `noryx7_operational.py`, `gateway/runtime_adapter.py` | durable audit injection #61; sandbox #68; identity revalidation #71 | one composition root, no bypass path, injected mandatory security dependencies |
| Execution fabric | `core/execution_fabric.py`, `core/provider_execution.py`, `core/actions.py`, `core/tools.py`, `core/job_supervisor.py`, `noryx7_runtime/engine.py` | process executor #27/#34/#36/#39; Bubblewrap #45/#53/#62/#68/#71 | timeout, process-tree kill, cancellation, idempotency, target-side authorization and audit |

## Security, identity and evidence

| Domain | Main baseline paths | PR-only additions / related PRs | Required verification |
|---|---|---|---|
| Identity and trust | `core/identity.py`, `core/agent_identity.py`, `core/trust_chain.py`, `core/attestation.py`, `core/secure_boot.py` | durable registry #26/#46; strict runtime #31; collaboration revalidation #64/#71 | identity epochs, revocation fencing, key rotation, restart persistence |
| Policy and authorization | `core/policy.py`, `core/authorization_replay.py`, `core/multiauth.py`, `core/security.py`, `core/architecture_gate.py` | plan-bound auth #16; replay #18/#23; atomic agent dispatch #48 | least privilege, replay, race conditions, policy version pinning, fail-closed behavior |
| Cryptographic lifecycle | `core/crypto.py`, `core/key_lifecycle.py`, `core/secure_channel.py`, `core/secure_storage.py` | durable key state #29/#32/#43; lifecycle-bound provider #51 | crash-safe rotation, revocation, opaque handles, no raw root key exposure |
| Audit and durable evidence | `core/audit.py`, `core/execution_trace.py`, `core/state_journal.py`, `core/offline_anchor.py` | thread-safe audit #44; audited execution #56; SQLite chain #57; runtime injection #61; external anchor #65; quorum integration #66 | sequence integrity, concurrent append, crash gaps, rollback detection, privacy-safe logs |
| Remote witness / quorum | `core/offline_anchor.py`, `core/trust_chain.py` | remote witness #38; witness authority #41; HTTPS/mTLS #49; quorum #63/#66 | independent trust domain, monotonic state, partition policy, strict quorum and rollback |

## Memory, data and distributed device fabric

| Domain | Main baseline paths | PR-only additions / related PRs | Required verification |
|---|---|---|---|
| Memory hierarchy | `core/memory.py`, `core/memory_hierarchy.py`, `core/secure_memory.py` | hierarchy hardening #42; encrypted store #15/#20/#28 | owner/session/tenant scoping, concurrency, retention, encryption, deletion |
| Distributed memory | `core/distributed.py`, `core/device_fabric.py` | causal replication #47/#52/#55/#59/#70; HTTPS/mTLS #54/#58/#67; tiered router #37 | vector-clock closure, contiguous counters, peer identity, replay and partition recovery |
| Matrix / resource network | `core/device.py`, `core/device_fabric.py`, `core/resource_router.py`, `core/control_plane.py`, `core/system_fabric.py` | Matrix Core #73 adds `core/matrix_*` family | opt-in grant, reservation, owner revocation, fencing, quotas, energy/thermal budgets |
| Data Fabric | `core/secure_storage.py`, `core/secure_memory.py`, `core/egress.py`, `core/distributed.py` | distributed memory PR family | encryption at rest/in transit, manifest integrity, data locality, retention and restore drills |
| Network / egress | `core/secure_channel.py`, `core/egress.py`, `core/http_provider.py`, `noryx7_runtime/adapters.py` | mTLS memory peer #54/#58/#67; witness transport #49 | DNS/redirect policy, SSRF, request bounds, replay, certificate-to-principal binding |

## Inspection, simulation, resilience and interfaces

| Domain | Main baseline paths | PR-only additions / related PRs | Required verification |
|---|---|---|---|
| SURF / system inspection | `core/surf_contracts.py`, `core/supply_chain.py`, `core/cyber_range.py`, `core/verification.py` | system inspector #50; ELF #69; Python mapper #60; integration #72; signed receipts #17 | static non-execution, bounded parsers, authorization scope, reproducibility, false-positive controls |
| Simulation / test lab | `core/cyber_range.py`, `core/evaluation.py`, `core/evaluation_campaign.py`, `core/adversarial.py` | multi-sector campaign #12/#13/#22 | deterministic seeds, bounded workloads, fault injection, independent expected outcomes |
| Self-management / recovery | `core/recovery.py`, `core/self_improvement.py`, `core/supervisor.py`, `core/job_supervisor.py`, `noryx7_runtime/recovery.py` | durable journal #14/#19/#24/#25/#38/#40/#41; process containment #39 | staged repair, canary, rollback, crash recovery, no self-granted privilege |
| Offline continuity | `core/offline.py`, `core/offline_adapters.py`, `core/offline_anchor.py`, `noryx7_runtime/recovery.py` | causal replication and durable witness PRs | disconnected local operations, stale-policy denial, sync conflict and rollback |
| Gateway / APIs | `gateway/server.py`, `gateway/auth.py`, `gateway/runtime_adapter.py`, `gateway/__main__.py` | canonical runtime integrations #61/#68/#71 | session scope, auth, request limits, idempotency, runtime parity |
| Browser / device clients | `core/device.py`, `core/device_fabric.py`, `tests/test_browser_isolation.py`, `tests/gateway/test_gateway_e2e.py` | Android/browser paths not represented in the current 65-PR implementation stack | permissions, isolation, privacy, offline, lifecycle and consent |

## Ecosystem and governance

| Domain | Main baseline paths | PR-only additions / related PRs | Required verification |
|---|---|---|---|
| Finance / marketplace | `ecosystem/global_fabric.py`, `core/supply_chain.py` | no dedicated finance/marketplace PR confirmed in current open inventory | ledger correctness, authorization, idempotency, compliance, disputes |
| Community / governance | `ecosystem/global_fabric.py`, `core/user_understanding.py`, `core/policy.py` | no dedicated governance/community PR confirmed | consent, transparent policy, appeal, privacy, non-coercion |
| Critical infrastructure | `core/device.py`, `core/defense.py`, `core/policy.py`, `core/verification.py` | no dedicated certified-control integration PR confirmed | independent interlocks, manual override, hazard analysis, no LLM actuator authority |
| Observability / operations | `core/observability.py`, `core/alerting.py`, `core/platform.py`, `core/limits.py` | CI/test workflows in #8/#12/#22 and sandbox workflow #62/#71 | SLO evidence, privacy-safe telemetry, deployment/rollback and incident runbooks |

## Confirmed baseline test families

Main contains dedicated test modules for HYPERSYNTH, agents, identity, authorization, memory, runtime, offline, secure storage, sandbox boundaries, gateway, provider resilience, recovery, observability, supply chain and global infrastructure. Examples include:
- `core/test_hypersynth_acceptance.py`, `core/test_hypersynth_adversarial.py`, `core/test_hypersynth_runtime_contract.py`
- `core/test_agent_fabric.py`, `core/test_identity_boundaries.py`, `core/test_authorization_replay.py`
- `core/test_memory_boundaries.py`, `core/test_secure_memory.py`, `core/test_secure_storage.py`
- `tests/test_operational_runtime.py`, `tests/test_runtime_dispatch.py`, `tests/test_runtime_identity_binding.py`
- `tests/test_offline.py`, `tests/test_recovery_atomicity.py`, `tests/test_recovery_security_boundary.py`
- `tests/test_global_infrastructure_closure.py`, `tests/test_ecosystem_boundaries.py`, `tests/test_supply_chain_strictness.py`

## Critical findings from the inventory

1. The main branch already contains a substantial cognitive/runtime/security foundation; rewriting it wholesale would duplicate working code and increase integration risk.
2. Several important capabilities are currently visible only in open PR branches: Matrix Core (#73), process isolation/deadlines (#27/#34/#36/#39), durable identity (#46), distributed memory (#47+), remote witness/quorum (#38/#41/#63), SQLite audit (#57/#65), OS sandbox (#45/#62), and System Inspector (#50/#69/#72).
3. The architecture is not yet fully traceable to one canonical implementation. Several domains have parallel or overlapping modules and must be reconciled before they can be called integrated.
4. Finance, marketplace, governance, certified critical-control integration and some client surfaces are specified at architecture level but do not have dedicated implementation PRs in the current open PR inventory.
5. Every status beyond BASELINE/PR-ONLY remains unproven until the relevant exact commit has tests and review evidence.

## Exit criteria

A domain can move from DESIGNED to IMPLEMENTED only when its owning files and tests are identified. It can move to INTEGRATED only when the cumulative dependency branch includes all required parents and has no unresolved overlap. It can move to VERIFIED only when CI and targeted adversarial/recovery evidence pass on the exact candidate SHA. Deployment requires separate environment evidence.
