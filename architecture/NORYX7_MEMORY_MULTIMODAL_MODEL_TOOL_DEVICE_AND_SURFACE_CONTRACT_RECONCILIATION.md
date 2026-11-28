# NORYX7 — Memory, Multimodal, Model, Tool, Device and Surface Contract Reconciliation

**Date:** 2026-11-25 · **Source snapshot:** `fea4eaae990590c65ee564a8ffa37697e5f2ab42`  
**Mode:** architecture-only, bounded source inspection. No runtime, tests, dependencies, workflows, configuration, deployment or frozen baseline changed.

## 1. Evidence discipline

This pass continues W01–W12 through shared data, authority and surface contracts. A local primitive is not a complete production service: encryption is not durable storage; a digest is not authenticity; a model MAC is not correctness; a registered tool is not permission; a device grant is not remote attestation; a static browser scan is not a sandbox; an event buffer is not durable audit.

## 2. Exact source anchors

| Path | Blob SHA | Observed scope |
|---|---|---|
| `core/memory.py` | `1fc3ca97ab6239d045964b55c3d13f2fc7e6d9cd` | bounded in-process MemoryStore, deep-copy and execution filter |
| `core/memory_hierarchy.py` | `d908fcb7252e97072501b94dada23ae571807850` | bounded L0–L5 key/value hierarchy |
| `core/secure_memory.py` | `27727ce69802f3ad4f082bf4b9bc4ef013fa7812` | encrypted MemoryItem serialization adapter |
| `core/secure_storage.py` | `0fd726f2bad1ff6e133b46c04039ae2c943d350f` | encrypted record map, namespace/record AAD |
| `core/crypto.py` | `ce0f534fb6f786838325dc22469c2364aee4ee9b` | AES-256-GCM, HKDF, key provider |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` | media refs and canonical request digest |
| `noryx7_runtime/model_fabric.py` | `abb8bd9bb3217fff967e898afbdc491eb5082f45` | model candidate filtering, cost/latency/capability constraints |
| `core/llm/model_fabric_bridge.py` | `544dd80facf249278adbb797b276f82935564305` | text-only bridge, no model tool dispatch |
| `core/llm/agent.py` | `c2dc54757bb516ced4e36fd7590f675ba1a74475` | model-backed agent and metadata |
| `core/tool_protocol.py` | `1c529fbbf5352469be8ab6633edc48113da8a3bf` | ToolSpec registry with injected authorization callback |
| `core/tools.py` | `a5c2797cce7c803abb272bab761b3288ba0f7e72` | capability registry and ActionGate-backed ToolExecutor |
| `core/agent_skills.py` | `281d294ee0142a8dd33db5d61f634f95943db231` | declarative skills; registration does not grant authority |
| `core/resource_router.py` | `4f7bf28200edd05f1236d9779437e4aa43bba8ab` | deterministic device/edge/cloud tier selection |
| `core/device.py` | `4f7d82ec5a1e40b595c4c341ab7d3ed551f3ac14` | device identity, audience/epoch capability gate |
| `core/device_fabric.py` | `3b0ead031e03040d25bb7df3a716aaa50fa8591c` | in-process device registry |
| `core/system_fabric.py` | `cf28bd8a144480467b6bd2cf3726b510a7b7924f` | shared JARVIS/NORYX7 object-identity assertions |
| `core/jarvis_runtime_bridge.py` | `0f5611bdccfa917c601a34b471c198a65fcbd48c` | JARVIS plan to RuntimeEngine/ToolExecutor bridge |
| `jarvis/core/runtime.py` | `09134dbd587b118f43dfbd07a6c054eddedd1cc8` | JARVIS composition, provider paths and canonical fabric |
| `jarvis/agent/front_end.py` | `b34314c24cebf2435202716035ff6b83ebbfacd1` | wake-session frontend and text input |
| `jarvis/perception/audio.py` | `c2b8fa33f13124a6a6f8ae4b0c3274e914ccd95a` | deterministic clap-pattern detector |
| `jarvis/interaction/session.py` | `48644641728dc461f72c90c1dcf102f23bc23a48` | local wake-session lifecycle |
| `ecosystem/browser_isolation.py` | `73f69b55f7bb6335d6e9294c7d48ebac1868991a` | static source isolation scanner |
| `core/observability.py` | `05dea0228b9b05c8684db7fe0aa890d7faa44485` | bounded process-local security event bus |
| `noryx7_runtime/scheduler.py` | `5d87d38e17c93dd26975119bb3af1dddd6c132b9` | topological ordering, not concurrent dispatch |

## 3. Memory and context custody — W03/W06/W08/W09

**Positive controls:** MemoryStore validates IDs/kinds/execution IDs and deep-copies values; MemoryHierarchy bounds record count and supports explicit level promotion; EncryptedMemoryStore serializes a versioned MemoryItem; EncryptedRecordStore authenticates namespace and record identity as AAD and exposes ciphertext snapshots.

**Unresolved boundary:** MemoryStore, MemoryHierarchy and EncryptedRecordStore retain records in process-local dictionaries. L0–L5 records contain only key/value/level. EncryptedRecordStore documents a replaceable production backend but does not implement durable database/object storage, replication or disaster recovery. The MemoryItem schema does not cover full tenant/purpose/consent/retention/deletion/replica custody.

Canonical MemoryRecord must bind tenant, principal, agent, session, task and execution; source class and derivation lineage; purpose/legal basis, sensitivity and residency; created/observed/expiry/retention times; key ID/version; access/disclosure history; tombstones, deletion propagation/legal hold; replica acknowledgements and restore evidence. Context hydration must distinguish COMPLETE, EMPTY, PARTIAL, STALE, DENIED, UNAVAILABLE and CORRUPT; a read failure must not silently look like an empty memory.

## 4. Cryptographic custody — W02/W03/W08/W09

The source uses AES-256-GCM, a 96-bit nonce, 128-bit tag, key-ID binding and HKDF-SHA256 domain separation. The in-memory key provider is explicitly test-only; KeyProvider is an interface, not a production KMS. Ciphertext storage remains process-local. This pass does not establish HSM/KMS custody, root rotation, re-encryption, backup/restore, revocation, tenant key separation or destruction.

Required lifecycle: root-key custody, derivation domains, key ID/version, encrypt/decrypt authorization, rotation/re-wrap, compromise/revocation, offline-device compatibility, backup/restore, audit and destruction/legal hold.

## 5. Multimodal provenance — W06/W08/W09/W10

MediaRef supports text/image/audio/video/document and stores content type, SHA-256 digest and locator. MultimodalInput hashes the ordered canonical representation. This establishes request identity, not that locator bytes are authentic, available or consented. It does not prove capture identity/time, rights, transformations, OCR/ASR/frame lineage, temporal alignment, model/preprocessing version, human correction or claim-to-source entailment.

Required pipeline: ingest and validate → hash original → establish source/capture/rights/consent → encrypted payload custody → immutable transformed artifacts → model/preprocessing manifest → timestamps/segments → claims with exact source spans → verification → retention/deletion. Metadata and media payload custody remain distinct but linked.

## 6. Model and cognitive authority — W02/W04/W05/W06/W10

ModelRequest supports required/preferred capabilities, cost/latency limits, min/max model fan-out, tools, runtime ID and execution ID. ModelFabric filters eligible candidates and can be runtime-bound. The inspected LLM bridge requests text-only generation, one model and no tools. This is positive evidence that model reasoning is separated from tool authority.

Fan-out structures do not prove independent provider/model failure domains, calibrated consensus, factual correctness or source evidence. Every invocation needs request/parent/execution IDs, model/provider/version, residency, prompt/context digest, policy epoch, budget/deadline, attempt ID, output digest, finish reason, verification and provenance. Model output remains an untrusted proposal until a typed verifier admits it; consensus must account for correlated providers and shared failure modes.

## 7. Tools, capabilities and skills — W02/W04/W05/W07/W08

ToolRegistry invokes a handler only after its injected authorization callback returns exactly True and records a simple ToolResult. ToolExecutor resolves a capability and uses ActionGate before output verification. AgentSkillRegistry is declarative and explicitly separates registration from permission. These paths must not be conflated: ToolExecutor has the stronger canonical gate; ToolRegistry relies on the caller's authorization implementation.

Required convergence: every executable tool, skill, browser/device action and external integration resolves into canonical ActionSpec/StepInvocation and crosses the same authorization/effect/evidence lifecycle. Tool contracts need input/output schemas, versioned capabilities, side-effect/idempotency class, deadlines, budgets, cancellation, isolation, egress, secret access, residency, audit and typed effect outcomes. Direct handlers must not bypass the canonical gate.

## 8. Device, resource placement and scheduling — W05/W07/W08/W09/W11

DeviceCapabilityGate checks VERIFIED trust, audience, expiry and epoch. DeviceFabric is an in-process registry with first-match online capability lookup. These do not prove hardware attestation, secure boot, key custody, remote revocation or network reachability.

ResourceRouter chooses device/edge/cloud using deterministic complexity/privacy/latency thresholds; it does not reserve capacity, attest a node, prove residency or confirm execution. Scheduler validates dependency IDs/cycles and produces topological order; it does not execute independent steps concurrently.

Required PlacementLease: node attestation, residency, capacity/quota reservation, lease expiry/fencing token, queue/deadline, cost/energy budget, data locality, failure domain, transfer encryption, cancellation/retry and completion receipt. Planning order, actual parallelism and reserved execution capacity are separate facts.

## 9. JARVIS and interface convergence — W01/W02/W04/W07

CanonicalSystemFabric asserts that JARVIS and NORYX7 share the same RuntimeEngine, ToolExecutor, verifier, authorization authority, principal and policy objects. JarvisRuntime composes this fabric and JarvisRuntimeBridge maps JARVIS PlanSteps through RuntimeEngine and ActionGate-backed ToolExecutor. This is positive convergence evidence and refines the earlier finding that these stacks were simply independent.

Remaining gaps: JarvisRuntime constructs ProviderExecutionGateway and ResilientProviderExecutor separately; provider retry/effect ownership remains open. Its default RuntimeEngine construction does not establish durable journal injection. JarvisFacade can construct local defaults, so production composition and lifecycle still need specification. The inspected audio frontend detects clap patterns and activates a local wake session before text input; this is not proof of streaming speech recognition, diarization, voice identity or multimodal dialogue. Wake activation is never action authorization.

Required interface envelope: authenticated principal/session, modality and consent, capture provenance, retention, interruption/cancellation, false-wake policy, voice-biometric separation, accessibility, offline behavior, explicit action confirmation and session-to-execution lineage.

## 10. Browser and observability — W08/W09/W11

The browser isolation scanner strips comments/quoted strings and statically checks Android browser source for direct model/runtime/chatbot/telemetry markers. This supports the intentionally AI-free WebView front and explicit gateway boundary. It is not a Chromium process-sandbox audit, OS permission review, egress firewall, TLS lifecycle, cookie partitioning, download security or penetration test.

SecurityEventBus holds bounded in-memory typed events with severity, timestamp and evidence digest. It is not durable tamper-evident audit, remote retention, alerting, containment, SIEM delivery, clock synchronization or incident response. Full-buffer failure handling remains an integration concern.

Required surface controls: renderer/native/gateway/runtime trust zones, origin and URL policy, download and external-intent confirmation, cookie/storage partitioning, egress allowlist, session-token custody, signed updates and rollback. Required observability: globally unique event IDs, trace/parent execution IDs, actor/authority/policy/target/effect receipt, durable append, tamper evidence, delivery acknowledgement, privacy redaction, alert thresholds, containment playbooks and retention.

## 11. Cross-workstream closure map

| Workstream | Added source evidence | Still required |
|---|---|---|
| W01 Core/system | JARVIS and core share CanonicalSystemFabric identity assertions | production composition root and ingress/provider convergence |
| W02 Security | ActionGate ToolExecutor; device audience/epoch gate | shared distributed revocation and surface/tool authority |
| W03 Memory/state | encrypted MemoryItem adapter and L0–L5 primitive | durable backend, tenant scope, retention, deletion, typed hydration |
| W04 Agents | skill registration separated from permission | parent/child lineage across skills and effects |
| W05 Routing | deterministic tier selection and DAG ordering | real leases, capacity, concurrency, attestation |
| W06 Cognition | multimodal digest and model invocation constraints | source authenticity, claim spans, calibration, independent verification |
| W07 Interfaces | device gate and JARVIS wake-session frontend | platform attestation, consent, confirmation |
| W08 Distribution/privacy | AAD and browser source-isolation gate | production keys/storage, egress, durable event fabric |
| W09 Operations | security event schema | durable telemetry, incident response, deployment assurance |
| W10 Domains | model capability constraints | domain qualification and evidence standards |
| W11 Reliability | bounded memory/model fan-out/scheduler | end-to-end budgets, backpressure, concurrency, degradation |
| W12 Ecosystem | no new production financial/impact evidence in these paths | ledger/payment authority and independent outcome verification |

## 12. Canonical shared object graph

Converge on versioned immutable envelopes: PrincipalAssertion; InteractionEnvelope; MediaArtifact; MemoryRecord; CognitiveRequest; Hypothesis/Claim/Evidence; StepInvocation; ActionAuthorization; Tool/Device/ProviderAttempt; EffectReceipt; PlacementLease; AuditEvent/ReleaseEvidence. Each needs canonical serialization, stable identity, schema version, digest, owner, policy, retention and migration rules. A digest chain without source authenticity or trusted time proves only an integrity relation.

## 13. Disposition

No new ADR ID is created. Existing decisions on memory/crypto/multimodal, tools/providers, device/resource placement, browser isolation and observability remain OPEN. W01–W12 remain **PARTIAL**. This document is not implementation, test, certification, merge or release evidence. The next architecture pass must finish the remaining constructor/consumer map for media ingestion, memory hydration/promotion, key-provider injection, model callers, tool registry callers, device adapters, browser gateway and observability consumers before integration.
