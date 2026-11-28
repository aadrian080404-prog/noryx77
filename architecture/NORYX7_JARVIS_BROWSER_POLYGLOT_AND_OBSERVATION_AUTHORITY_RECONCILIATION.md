# NORYX7 — JARVIS, Browser, Polyglot Runtime and Observation Authority Reconciliation

**Audit date:** 2026-11-27  
**Audited source-tree HEAD:** `e463e5a003cebe3d8e9b6ea2d384f0c703a3bcff`  
**Scope:** W01–W12 cross-plane reconciliation with focus on JARVIS runtime/facade, HYPERSYNTH, browser/device ingress, observation and voice, Go/Rust runtime surfaces, state/audit custody, and the evidence boundary into NEXUS/FRL and MIRROR WORLD.  
**Disposition:** architecture-only source audit and proposed closure contracts. No implementation, tests, dependencies, workflows, deployment or frozen baseline changed.

## 1. Executive finding

NORYX7 already contains several meaningful execution and interface layers: HYPERSYNTH, a standalone JARVIS runtime/facade, the canonical Core ActionGate/ToolExecutor bridge, an Android Browser gateway client, authorized observation/context adapters, a deterministic audio wake detector, a Go gateway stub and a Rust execution-envelope primitive.

The important unresolved question is not whether these pieces exist. It is whether they share one authenticated request identity, one policy decision, one operation lifecycle, one durable state owner and one evidence model. The inspected source shows multiple boundaries which must remain explicit until an authoritative composition root and versioned adapters connect them.

Key conclusions:
- JARVIS has both a legacy request/plan policy and Core identity/authorization/action infrastructure. The same runtime also instantiates separate provider execution and resilience paths.
- The JARVIS facade constructs the request principal as the literal `"user"`; the audio front end marks wake metadata as `verified_wake=True`, but that is session metadata, not user identity or action authorization.
- JARVIS plans are supplied to the facade; the built-in Decomposer returns a single deterministic compute step. This is not yet a complete perception-to-branching-cognition interface.
- JARVIS state reservations, commits and hash-chained audit records are in-memory structures in the inspected implementation. Their local integrity semantics do not establish crash durability or remote audit anchoring.
- Browser navigation policy permits well-formed HTTPS main-frame URLs, but that alone is not a complete network destination/egress policy. The gateway client uses a bootstrap token and client ID to obtain a session; the client ID is not independently an enrolled device identity.
- ObservationFabric stamps provenance as `authorized:<source_id>`; this identifies an authorization path in local code, not signed sensor provenance or measured-world truth.
- Go `/digest` and Rust `canonical_digest` are distinct low-level primitives, not one interoperable signed execution protocol. Neither inspected surface defines the canonical NORYX7 schema/version, issuer, audience, nonce/replay rules, operation/effect receipt or cross-language signature contract.
- NEXUS/FRL must admit source-anchored claims and proof artifacts only within explicit scope. MIRROR WORLD simulations and Browser observations must not be promoted to empirical reality without separately authenticated observation receipts.

## 2. Source anchors

Blob IDs identify the source files inspected at the audited tree:

| Source | Blob SHA | Bounded observation |
|---|---|---|
| `core/hypersynth.py` | `187699d6e0945a2b1e8a9b194cd9001b1af8cd9f` | Cognitive kernel phases, bounded planner/agent limits, ActionGate, supervisor, hypothesis/simulator/metacognition and optional ToolExecutor |
| `jarvis/ARCHITECTURE.md` | `95cc88273a242a9154558d7b9d3cb74c4956594f` | Proposed JARVIS request→identity→plan→policy→capability→executor→result→audit boundary |
| `jarvis/core/runtime.py` | `09134dbd587b118f43dfbd07a6c054eddedd1cc8` | Runtime composes legacy orchestrator/policy, Core ActionGate/ToolExecutor, generated JARVIS agent identity, RuntimeEngine bridge, plus separate provider execution/resilience objects |
| `jarvis/core/contracts.py` | `bb1338248f68a627b292cf4e475f4b64eff9662c` | Request/Plan/PlanStep/ActionResult contracts and limits |
| `jarvis/core/decomposition.py` | `bde8c9466a8c78b51befb3086b66a66f48f9d72d` | Default decomposer emits one deterministic compute step using request text as target |
| `jarvis/runtime_facade.py` | `b1a50f1c8c6566804151f81daf93114205f2afb9` | Facade builds request with literal principal `user` and accepts caller-supplied Plan |
| `jarvis/agent/front_end.py` | `b34314c24cebf2435202716035ff6b83ebbfacd1` | Wake activates a session; input metadata includes `verified_wake=True` |
| `jarvis/perception/audio.py` | `c2b8fa33f13124a6a6f8ae4b0c3274e914ccd95a` | Deterministic clap-pattern detector explicitly does not authorize actions |
| `jarvis/observation/fabric.py` | `1d4a081b38a3c377929436ce7e8ea6a4531a530f` | Local reader registry, callback authorization and textual provenance label |
| `jarvis/context/authorized.py` | `339cef4a01efbb34293ebcd93eff1289e4fec5c2` | Callback-gated context acquisition with local source provenance |
| `jarvis/core/state.py` | `7895e63ff82a7d3d0d147eb41c4e1b1fb4c2bc2f` | Thread-safe in-memory reservations and commits; commit accepts caller boolean `verified_results` |
| `jarvis/security/audit.py` | `d92b9b6347b3d1989dbb553ea530729f7fafcaaa` | Append-only in-process hash chain with local verification |
| `jarvis/security/authorization.py` | `dd7db5e133632061bbfbac88ed47bede27bc387c` | In-memory exact principal/capability/target grants |
| `jarvis/tools/registry.py` | `aeb2464971f196fac882971ed2a0f7f2cf0a60fb` | JARVIS capability adapter reconstructs PlanStep and ActionResult at Core registry boundary |
| `noryx-browser/app/src/main/java/com/noryx/browser/NavigationPolicy.kt` | `d1fb80964f4319929a6054742101c996ea8abf53` | Main-frame URL requires HTTPS, host and no userinfo |
| `noryx-browser/app/src/main/java/com/noryx/browser/NoryxWebViewClient.kt` | `3939342eef0757250b76fe2f06bf714d7a7e9243` | Applies policy to main-frame navigation callbacks |
| `noryx-browser/app/src/main/java/com/noryx/browser/NoryxGatewayClient.kt` | `c759625005c13cc706f36aa91160267bff25b8ca` | Bootstrap-token/client-ID session creation and bearer-token execution |
| `services/jarvis-gateway-go/main.go` | `1d9baa84b229ad8056be69f3a0955ead3d1f981e` | Minimal health endpoint and POST body digest endpoint |
| `services/jarvis-runtime-rs/src/lib.rs` | `035960c0d08f1db5825f01a78ce314f7055516c0` | Three-field ExecutionEnvelope, JSON SHA-256 digest and boolean deny-by-default helper |
| `core/multimodal.py` | `8c3fb71a6277806d98c2c294444443ddcc3ff9ee` | MediaRef stores modality/type/digest/locator; no custody/consent/rights semantics |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` | Synthetic sandbox targets and symbolic actions only |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Bounded event graph and heuristic relevance/anomaly/forecast primitives |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Trusted Ed25519 manifest and artifact-byte digest verification |

## 3. Cross-plane findings

### 3.1 HYPERSYNTH and JARVIS are related but not yet one cognitive/runtime authority

HYPERSYNTH is the NORYX7 cognitive pipeline. It accepts verifier/router dependencies and composes decomposition, context, planning, hypotheses, internal simulation, allocation, execution, verification and metacognition. Its current bounded path must not be described as a general parallel branching engine merely because it has hypothesis and simulation stages.

JARVIS has a separate Request/Plan/PlanStep contract and a standalone orchestrator. JarvisRuntime additionally composes Core ActionGate/ToolExecutor, a generated JARVIS agent identity, RuntimeEngine/JarvisRuntimeBridge and CanonicalSystemFabric. It also constructs ProviderExecutionGateway and ResilientProviderExecutor as distinct provider paths.

The facade currently receives a Plan from its caller and creates a Request with principal `user`. The default Decomposer is a one-step deterministic stub. Therefore, a successful JARVIS call does not establish that HYPERSYNTH decomposition, branching, NEXUS evidence review, MIRROR WORLD validation and final ActionGate admission all participated in the same execution.

**Required closure:** define a single CognitiveExecutionEnvelope with request/goal ID, authenticated human/service principal, agent identity, tenant/device, execution and operation IDs, policy epoch, branch/DAG manifest, context/evidence references, resource budget, risk class and explicit handoff stage. JARVIS should be a surface/runtime adapter, not a competing source of cognition or policy. HYPERSYNTH should emit a typed proposal/plan; only the canonical authorization/execution plane may admit side effects.

### 3.2 Wake, speech, observation and context are not identity or truth

The clap detector returns a WakeEvent; the frontend activates a local session and sets a metadata flag. VoiceGateway can transcribe and synthesize through an injected provider. Neither voice transcription nor wake detection proves who is speaking, what device is enrolled or whether a requested action is authorized.

ObservationFabric invokes a registered reader after callback authorization and emits a textual provenance marker. This proves only that the local callback approved a source ID at call time. It does not prove sensor attestation, timestamp integrity, calibration, physical location, consent, source custody, tamper resistance or independent corroboration.

AuthorizedContext has the same boundary: it gates access to registered readers but does not authenticate the underlying content or establish truth.

**Required closure:** separate WakeSession, AuthenticatedPrincipal, DeviceAttestation, SensorSourceAttestation, ObservationReceipt and ActionAuthorization. A wake event can open an interaction session but must never grant a capability. Speech-to-text is untrusted input until bound to a session and principal. Observations need signed source identity, monotonic time/clock quality, calibration, raw payload digest, custody chain, consent/purpose, measurement uncertainty and independent corroboration where required.

### 3.3 JARVIS state and audit are locally coherent but not durable by construction

JarvisStateStore provides locks, reservations, sequence values and verified-only commit shape. The commit call accepts a boolean `verified_results=True` default; the store validates the caller assertion rather than consuming a cryptographically bound VerificationReceipt. The inspected maps and sequence live in the process.

AuditLog builds a verifiable hash chain over in-memory events. This detects modifications relative to the current in-memory chain but does not by itself provide persistence, external checkpointing, signer identity, anti-truncation, trusted timestamping, retention, export or incident delivery.

The JARVIS runtime also maintains an in-memory bounded execution_traces map. These three local stores are not one durable transaction. A process restart can lose reservations, commits, audit history and traces unless an external persistence adapter is composed and verified.

**Required closure:** define one state/audit adapter contract with append-only durable commit, transaction ID, previous checkpoint, signed checkpoint cadence, anti-truncation witness, restore test evidence and explicit retention. A commit must consume a typed VerificationReceipt tied to exact result digest, verifier profile, execution, policy epoch and scope—not a caller boolean.

### 3.4 Browser ingress and gateway session require identity, origin and egress closure

NavigationPolicy requires HTTPS, a host and no userinfo. NoryxWebViewClient applies it to main-frame navigation. This is a useful transport/syntax baseline, not a complete destination policy: it does not itself establish hostname allowlists, DNS/private-address checks, redirect-by-redirect policy, certificate/pinning policy, download/content policy or subresource egress controls. These may be provided elsewhere; this audit does not infer their universal absence.

NoryxGatewayClient authenticates with bootstrap token and client ID, receives a session token and sends it as a bearer token to `/v1/execute`. The client ID is a supplied string in this client contract; the source alone does not show device enrollment, hardware attestation or principal binding. The client accepts response status `completed` plus a verification object with `valid=true`; this is a response-shape gate, not independent verification of the server's evidence.

**Required closure:** bind enrollment and session to authenticated principal, device key/attestation, audience, allowed origins, tenant, expiry, nonce/replay window and policy epoch. Browser navigation, subresource fetch, downloads, external intents and gateway egress need separate policy decisions. The client should validate a signed server receipt bound to request/execution/result digest, verifier identity, schema version and commit status.

### 3.5 Go and Rust surfaces are not a canonical polyglot protocol

The Go service currently exposes health metadata and hashes arbitrary POST body bytes at `/digest`. The inspected handler reads the entire request body without an explicit local size cap, and does not implement authenticated operation dispatch. The Rust library serializes a small struct of execution ID/action type/target and returns a SHA-256 digest; `deny_by_default` takes a boolean. Neither implementation establishes a signed, replay-resistant, versioned operation envelope or a common canonical byte representation across languages.

A SHA-256 digest is not a signature, issuer assertion, authorization decision, execution receipt or proof of effect. Hashing arbitrary JSON bytes and hashing a Rust-serialized struct can produce different digests for semantically similar payloads unless a canonical serialization and schema are agreed.

**Required closure:** define a language-neutral schema registry, canonical JSON/CBOR encoding, strict size/depth/field limits, schema ID/version, issuer/audience, tenant/principal/device, operation/execution/attempt IDs, nonce, issued/expiry times, policy epoch, payload digest, signature suite and receipt lifecycle. Publish identical golden vectors for Go, Rust, Kotlin and Python. Every implementation must reject unknown critical fields, duplicate keys, unsupported versions, invalid signatures, expired/replayed envelopes and noncanonical encodings. A digest endpoint remains a diagnostic primitive, not a runtime authority.

### 3.6 NEXUS/FRL and MIRROR WORLD require evidence-type separation at the surface boundary

Browser pages, audio transcripts, sensor readings, provider responses, synthetic cyber-range events, FINCH hypotheses and simulated world outputs have different epistemic status.

A Browser page is a retrieved artifact, not a trusted instruction. A transcript is a derived representation, not the original audio. An ObservationEvent is a local adapter output, not a calibrated measurement. A CyberRange SimulationReport is synthetic, not a real-system observation. A FINCH Forecast is a heuristic hypothesis, not a probability unless calibrated. A cryptographic digest preserves byte identity but does not authenticate source truth.

**Required closure:** NEXUS claims must retain source artifact, immutable digest, exact span/time interval, acquisition method, transformation lineage, source authority, temporal scope, uncertainty, contradiction and reviewer. FRL proofs must name exact proposition, axioms/theory, checker build and proof artifact digest. MIRROR WORLD runs must bind model/world manifest, assumptions, calibration dataset, uncertainty, simulator build and synthetic-only classification. Reality Bridge admission requires a separately signed RealityObservationReceipt and human/policy authorization; no synthetic or model-generated output may self-certify its transition to real-world action.

### 3.7 W12 and public-impact actions need a distinct outcome ledger

The inspected JARVIS/Browser execution surfaces can provide a user interface and invoke capabilities, but they do not define a canonical W12 lifecycle for financial entries, settlement, refunds, governance votes, community contributions or environmental impact. A successful command or provider receipt is not proof that a payment settled, material was collected, emissions were reduced or a community outcome occurred.

**Required closure:** separate ContributionIntent, FinancialAuthorization, PaymentAttempt, SettlementReceipt, RefundReceipt, GovernanceDecision and ImpactObservation. Every environmental/social outcome must carry baseline, measurement method, source, time window, uncertainty, independent review and anti-double-counting identity. Financial state and physical impact state must never be collapsed into one success flag.

## 4. Cross-stream reference architecture

1. **Surface ingress (Browser/JARVIS/voice):** collect untrusted input; bind session, enrolled device and authenticated principal.
2. **Observation and custody:** produce typed source/media/sensor receipts; preserve raw artifact and transformations.
3. **Cognitive plane (HYPERSYNTH):** decompose, branch, hypothesize, retrieve NEXUS claims, request MIRROR WORLD experiments and produce an immutable proposal.
4. **Evidence plane (NEXUS/FRL):** authenticate sources, anchor claims, preserve contradiction, check exact formal artifacts and admit only scoped conclusions.
5. **Simulation plane (MIRROR WORLD):** execute isolated reproducible simulations and publish explicit uncertainty/fidelity.
6. **Authorization plane:** bind principal, agent, device, capability, target, purpose, risk, policy epoch and one-time grant to operation.
7. **Execution plane (RuntimeEngine/ToolExecutor):** dispatch one stable operation/attempt; return typed receipt with effect certainty.
8. **State/audit plane:** durably commit result/effect/evidence and signed audit checkpoint; reconcile unknown outcomes.
9. **Global operations plane:** schedule using fenced placement leases, durable resource reservation and measured deployment evidence.
10. **W12 outcome plane:** separately reconcile payment/settlement/governance/impact evidence.

This is a proposed responsibility map, not a claim that these layers are already composed.

## 5. Proposed shared contracts (not accepted ADRs)

- `CognitiveExecutionEnvelope`: request/goal, principal, agent, tenant/device, execution/operation, policy epoch, branch/DAG manifest, evidence/context refs, risk and budget.
- `DeviceEnrollmentReceipt`: device key, hardware/software attestation profile, owner/principal, allowed audiences, expiry, revocation epoch and issuer signature.
- `WakeSessionReceipt`: wake detector/version, event digest, device/session, timestamp quality and explicit `interaction_only` authority.
- `ObservationReceipt`: source identity, calibration, clock, raw payload digest, custody, consent/purpose, measurement method, uncertainty and reviewer.
- `VerificationReceipt`: exact output digest, verifier identity/profile/build, rubric, task/domain, scope, policy epoch, uncertainty and signature.
- `DurableAuditCheckpoint`: sequence range, previous checkpoint, chain head, signer, trusted timestamp, storage locator and anti-truncation witness.
- `PolyglotOperationEnvelope`: schema ID/version, canonical encoding, issuer/audience, principal/device/tenant, operation/execution/attempt IDs, nonce, times, policy epoch, capability/target, payload digest and signature.
- `PolyglotEffectReceipt`: receiver identity, operation/attempt, request/effect digest, target transaction, effect certainty, commit marker and signature.
- `BrowserEgressDecision`: origin, resolved addresses, redirect chain, resource type, principal/device/session, policy epoch and allow/deny reason.
- `RealityObservationReceipt`: independently authenticated observation and custody evidence used by Reality Bridge.
- `ImpactObservationReceipt`: baseline, unit, method, geography, time window, uncertainty, source and anti-double-counting key.

## 6. New bounded gap entries

- `GAP-JARVIS-HYPERSYNTH-COGNITIVE-PLANE-OWNERSHIP`
- `GAP-JARVIS-FACADE-PRINCIPAL-AND-PLAN-TRUST-BOUNDARY`
- `GAP-WAKE-VOICE-AND-OBSERVATION-AUTHORITY-SEPARATION`
- `GAP-JARVIS-STATE-AUDIT-DURABILITY-AND-VERIFICATION-RECEIPT`
- `GAP-BROWSER-DEVICE-ENROLLMENT-AND-EGRESS-POLICY`
- `GAP-POLYGLOT-CANONICAL-ENCODING-AND-SIGNED-OPERATION-PROTOCOL`
- `GAP-NEXUS-MIRROR-WORLD-REALITY-BRIDGE-EVIDENCE-ADMISSION`
- `GAP-W12-FINANCIAL-GOVERNANCE-AND-IMPACT-OUTCOME-LEDGER`

These are architecture closure requirements from bounded source inspection, not confirmed vulnerabilities or claims that no external controls exist.

## 7. Disposition

This pass does not authorize implementation, integration, testing, merge or freeze. The next architecture-only pass must map each external adapter and production composition root to the contracts above, identify one owner per authority/state/evidence boundary and resolve the remaining decisions. After W01–W12 architecture closure, proceed to integration, then comprehensive end-to-end verification and validation.

**W01–W12 remain PARTIAL.**
