# NORYX7 — Product Identity, Capability Boundaries and Realization Map

**Review date:** 2026-11-25  
**Reviewed branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source snapshot:** `bab155831256442e6018b78163c11c690f1547b9`  
**Mode:** architecture-only, bounded source reconciliation. No runtime, tests, dependencies, workflows, deployment or frozen baseline changes.

## 1. Executive definition

NORYX7 is intended to be a governed, distributed agentic operating platform: a common operational substrate that accepts a human or organizational objective, interprets it, decomposes it into bounded work, coordinates specialized agents and models, selects tools and execution locations, authorizes consequential actions, verifies outputs and effects, and preserves state and provenance.

It is not defined by a chat interface or by ownership of a single language model. A conversational surface may be one ingress channel; it is not the product's architectural center. The product's center is the controlled transition from **intent → evidence/context → plan → authorized execution → observed effect → verified result → durable state**.

The platform is meant to let a person, team, company, institution or community operate across software and, where explicitly connected and authorized, devices and physical workflows. It should make complex work easier to coordinate while keeping identity, permission, safety, evidence, privacy and accountability outside the discretion of generative models.

This is a statement of product intent and architectural identity, not a claim that the complete platform is already implemented or operational.

## 2. What the repository proves today

The source tree contains concrete components for:
- an 18-plane architecture registry and a structural completeness gate;
- bounded HYPERSYNTH cognitive phases, decomposition, planning, hypotheses, internal simulation, specialist routing and metacognitive checks;
- multiple agent execution abstractions, principal/identity checks, scoped authorization hooks and result admission;
- action authorization, capability registries, typed tool boundaries and runtime dispatch;
- model/provider routing and model adapters;
- local and hierarchical memory, encrypted-memory abstractions, multimodal references and cryptographic primitives;
- device, edge/cloud and global topology/resource primitives;
- runtime lifecycle, scheduling, attestation, journals and recovery;
- JARVIS runtime and Android NORYX Browser surfaces;
- research/evidence, evaluation, synthetic cyber-range, MIRROR WORLD and community/financial/impact architecture specifications.

The presence of these components is real source evidence. It does not establish that every component is wired into one canonical production composition, that all data is durable or replicated, or that every advertised capability is complete.

## 3. What NORYX7 is not

NORYX7 must not be described as:
1. **A chatbot with plugins.** Conversation is an interface; the core product is the governed execution and coordination substrate.
2. **A single LLM or model wrapper.** Models are replaceable proposal-producing components; they do not own identity, authority, state or truth.
3. **An autonomous unrestricted operator.** Tools, agents, devices, browser actions and external effects must cross explicit identity, capability, policy and verification boundaries.
4. **A proven AGI or sentient system.** The repository does not establish either claim; neither is required to define the product.
5. **A completed global distributed network.** Global registries and placement primitives do not by themselves prove durable multi-region replication, consensus, autoscaling, leases or disaster recovery.
6. **A calibrated digital replica of reality.** MIRROR WORLD architecture and synthetic simulation code do not prove validated physical, climate, economic or social prediction.
7. **A finished reverse-engineering product.** Systems understanding/reverse engineering is a planned capability requiring lawful scope, asset authorization, evidence standards and isolation; the inspected cyber range is synthetic and does not establish a general production reverse-engineering engine.
8. **A deployed social, financial or environmental movement platform.** Community, marketplace, ledger, payment and impact architecture are requirements and design boundaries, not proof of live operations or independently verified outcomes.

## 4. Operational model: what it should do

### 4.1 Objective intake and understanding
Accept tasks through approved interfaces; bind each request to a principal, session, tenant, source and consent context; normalize text, documents, images, audio, video and structured inputs; identify ambiguity and ask for clarification where needed. Understanding and profile signals must never grant authority.

### 4.2 Cognitive orchestration
Use HYPERSYNTH to decompose work, produce hypotheses and candidate plans, branch into specialist analyses, simulate bounded alternatives, retain disagreement and challenge weak conclusions. Cognitive outputs remain proposals until admitted by independent verification appropriate to the task.

### 4.3 Agent, model and resource coordination
Select agents and models based on task type, declared capabilities, trust, privacy, latency, cost and resource constraints. Keep model routing distinct from device/edge/cloud placement. A route or skill label is not an authorization grant or proof of professional qualification.

### 4.4 Governed execution
Translate approved plan steps into canonical action envelopes. Bind principal, execution, target, action, parameters, policy version, expiry, idempotency and authorization evidence. Execute through isolated adapters with bounded resources. A dispatched command, provider acknowledgement, observed external effect and committed result are separate facts.

### 4.5 Verification, memory and continuity
Verify structural correctness, source support, domain validity and effect evidence according to risk. Preserve source lineage and uncertainty. Admit only qualified results to durable state or long-term memory. Support expiry, correction, deletion, recovery, offline reconciliation and audit.

### 4.6 Distributed operation
Place workloads on device, edge or cloud without silently weakening privacy or trust. Require authenticated nodes, capacity reservation, bounded queues, explicit partition behavior and durable replication before making global-availability claims.

### 4.7 Human-facing surfaces
JARVIS is an interaction/runtime surface; NORYX Browser is a browsing surface; APIs and future clients are additional ingress/egress surfaces. No surface may bypass the common authority and effect lifecycle.

## 5. Product capability map and current realization boundary

| Capability family | Intended user value | Source-backed state | Remaining proof/closure |
|---|---|---|---|
| HYPERSYNTH cognition | Turn complex goals into structured work and hypotheses | Bounded phases and routing exist | End-to-end evidence semantics, branch execution, independent verification and canonical runtime ownership |
| Agent collaboration | Delegate work to specialized agents | Several agent fabrics and coordinator paths exist | One dispatch lifecycle, qualification, durable leases, DAG concurrency, lineage-aware consensus |
| Model fabric | Choose suitable models/providers | Runtime model fabric and adapters exist | Complete caller/bridge composition, policy-aware routing, receipt authenticity, retry/effect reconciliation |
| Tools and actions | Operate software/services under user permission | Tool registry, executor and ActionGate primitives exist | One canonical ActionSpec, adapter isolation, side-effect receipts, revocation and reconciliation |
| Memory | Retain useful context safely | In-process stores, L0–L5 hierarchy and encrypted abstractions exist | Durable backend, KMS/key custody, tenant lifecycle, replication, deletion propagation and restore |
| Multimodal | Understand and work with multiple media types | TEXT/IMAGE/AUDIO/VIDEO/DOCUMENT references and digests exist | Capture provenance, authenticity, consent, alignment, transformation lineage and semantic evidence |
| Device/edge/cloud | Execute close to data or at scale | Device registry, resource router and topology primitives exist | Hardware trust, capacity leases, durable control plane, scheduler, residency and failover |
| JARVIS / Browser | Give users practical interfaces | Runtime bridge, audio/session components and Android browser source exist | Unified authorization, production speech/perception, browser isolation and surface-to-runtime E2E evidence |
| NEXUS / research / evidence | Build traceable knowledge from sources | Evidence and research structures exist | Source custody, claim-span entailment, safe egress, independent source verification and epistemic lifecycle |
| MIRROR WORLD | Test scenarios and compare possible outcomes | Architecture and synthetic/sandbox primitives exist | Domain kernels, calibration, independent holdouts, uncertainty and Reality Bridge safety case |
| Systems understanding | Inspect and explain systems/software/protocols | Architecture proposal and cyber-range primitives exist | Explicit lawful asset scope, passive/active tiers, safe instrumentation, evidence sufficiency and production engine |
| Community / finance / impact | Coordinate projects, contributions and measurable outcomes | Governance and accounting architecture is specified | Regulated payment/ledger operations, custody, dispute handling, independent impact measurement and field validation |

## 6. Source observations that constrain product claims

### Cognition and planning
- `core/hypersynth.py` declares phases from perception/context through planning, hypothesis, simulation, allocation, execution, verification and metacognition. It bounds steps and agents; this does not prove all phases are independently calibrated or that independent DAG branches execute concurrently.
- `core/planning.py` and `core/decomposition.py` validate bounded plans/subtasks and dependencies. A valid plan is not a dispatched action.
- `noryx7_runtime/scheduler.py` produces dependency-safe topological order. `noryx7_runtime/engine.py` consumes the ordered steps sequentially in the inspected execution path.

### Authority and execution
- `core/tools.py` and `core/tool_protocol.py` provide distinct tool paths. One invokes a registered handler after an injected authorization callback; the other routes through capability and ActionGate-backed execution and output verification. They require canonical convergence.
- `core/system_fabric.py` provides a positive composition invariant by checking shared object identity for selected runtime/security components. This does not prove every facade, provider path, device and browser surface uses that composition.
- Runtime lifecycle, external side-effect certainty, result admission and durable commit remain distinct boundaries. FAILED after dispatch cannot be assumed to mean no external effect occurred.

### Memory, media and distribution
- `core/memory.py` is a bounded in-process store. L0–L5 hierarchy and encrypted-memory abstractions do not by themselves provide durable distributed storage, KMS-backed custody or disaster recovery.
- `core/multimodal.py` represents media modality, content type, digest and locator. A digest does not prove capture authenticity, consent, rights, semantic correctness or transformation history.
- `ecosystem/global_fabric.py` stores memory metadata and replica labels locally; replica count is not proof that independent durable replicas exist.
- `ecosystem/global_scale.py` provides region/cell/capacity selection primitives; it is not, by itself, a production global control plane or live capacity lease service.

### Evidence, domain intelligence and simulation
- `core/verification.py` performs structural/task/result checks. Structural validity is not factual truth or domain qualification.
- `core/universal_intelligence.py` routes by deterministic objective/context/risk keyword scoring. A specialist domain label is not evidence of expert qualification.
- `core/finch.py` computes forecast-shaped likelihood from mean event severity. This is a heuristic, not calibrated event probability.
- `core/evaluation_campaign.py` generates deterministic scenarios and holdout manifests; it does not itself execute independent evaluations or authenticate evidence producers.
- `core/cyber_range.py` is a synthetic/sandbox capability. Its existence is not proof of real-world system understanding or authorized penetration testing.

## 7. Canonical end-to-end object chain

The platform should converge on one versioned, typed chain:

1. **PrincipalAssertion** — authenticated user, organization, workload or device identity.
2. **InteractionEnvelope** — source surface, tenant/session, consent, modality, request and correlation IDs.
3. **EvidenceArtifact / MediaArtifact** — immutable source digest, custody, locator, capture time, transformations and rights/retention metadata.
4. **CognitiveRun** — task, hypotheses, specialist branches, uncertainty and evidence lineage.
5. **PlanDAG** — immutable steps, dependencies, budgets, deadlines, stop and compensation conditions.
6. **Delegation / PlacementLease** — agent identity, qualification scope, target node and reserved capacity.
7. **ActionSpec / AuthorizationGrant** — exact principal, action, target, parameters, policy, expiry and idempotency.
8. **Attempt / EffectReceipt** — dispatch state, provider/adapter acknowledgement, observed external effect and certainty.
9. **VerificationRecord** — structural, semantic, domain and effect evidence with reviewer/checker lineage.
10. **StateCommit / MemoryRecord** — durable admitted result, version, provenance, retention and deletion semantics.
11. **AuditEvent / ReleaseEvidence** — tamper-evident history, operational health, software provenance and release scope.

These are proposed canonical contracts, not claims that all objects already exist in the repository.

## 8. Product delivery sequence

1. Close the architecture and ownership decisions across all 18 planes and W01–W12.
2. Freeze canonical schemas, authority owners, state/effect lifecycles, evidence semantics and failure behavior.
3. Integrate the existing components through one composition root and compatibility adapters.
4. Run cross-surface security, recovery, offline, concurrency, fault-injection, semantic and domain validation.
5. Release a narrow, useful initial product (personal/team task orchestration with approved tools and transparent verification) before expanding to physical devices, global federation, MIRROR WORLD or public-impact finance.
6. Expand domain packages only when their qualification, calibration, liability and human-escalation requirements are met.

## 9. Non-negotiable product principles

- Models propose; policy and authority decide.
- Memory informs; it does not authorize or prove truth.
- Skills and agent count do not prove competence or independence.
- Simulation is not reality; a simulated result cannot actuate the world.
- A command receipt is not proof of its external effect.
- Privacy, consent, residency and deletion apply across caches, replicas and derived data.
- No silent trust downgrade from device to edge to cloud.
- Human approval and emergency stop remain available for consequential operations.
- Community impact is measured as independently verified outcomes, not clicks, pledges, activity counts or estimated emissions alone.
- A capability is not called complete until its owner, integration path, failure semantics and evidence are closed.

## 10. Closure impact

This product-level map binds W01–W12 to a single operating model without collapsing their authority boundaries. All workstreams remain **PARTIAL** until the architecture, source/call-site map, ownership decisions and acceptance evidence are closed. It authorizes no implementation, merge, deployment or architecture freeze.

## 11. Source anchors (blob SHA at reviewed branch)

| Source | Blob SHA |
|---|---|
| `core/architecture_gate.py` | `ed2e748821c0389672c747e9568b170de684c797` |
| `core/architecture_registry.py` | `2b90f6705be0e6ccf2474e94962c0d0c9539df43` |
| `core/hypersynth.py` | `187699d6e0945a2b1e8a9b194cd9001b1af8cd9f` |
| `core/planning.py` | `e9dbf86b1a90ce6d9e8a7af8445ddb73cbcaedd5` |
| `core/decomposition.py` | `b56af362124a307959355b5e252d0d960adfca52` |
| `core/resource_router.py` | `4f7bf28200edd05f1236d9779437e4aa43bba8ab` |
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` |
| `core/tool_protocol.py` | `1c529fbbf5352469be8ab6633edc48113da8a3bf` |
| `core/tools.py` | `a5c2797cce7c803abb272bab761b3288ba0f7e72` |
| `core/device_fabric.py` | `3b0ead031e03040d25bb7df3a716aaa50fa8591c` |
| `core/system_fabric.py` | `cf28bd8a144480467b6bd2cf3726b510a7b7924f` |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` |
| `core/universal_intelligence.py` | `986dd5976b6451a5a75950535c13f4355f57fb0f` |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` |
| `noryx7_runtime/scheduler.py` | `5d87d38e17c93dd26975119bb3af1dddd6c132b9` |

