# NORYX7 — Surface ingress, observation, global-scale and human-context reconciliation

**Review date:** 2026-11-22  
**Source baseline:** `main` at the PR base snapshot `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Change scope:** architecture-only; no runtime implementation, dependency, test, deployment or integration changes.

## 1. Purpose and relationship to the closure package

This document extends W01, W02, W05, W06, W08, W09 and W11 in parallel. It records direct source findings for the JARVIS provider/context/observation/perception surfaces, LLM-to-ModelFabric boundary, user-understanding consent model, cyber-range authorization, device/distributed/global-scale registries and FastAPI ingress. It does not replace ADR-002 through ADR-005 or claim any of their decisions are closed.

The key architectural distinction is between a *typed local contract* and a *production authority*. Several source components correctly model a bounded interface but do not yet provide durable identity, trusted evidence, remote revocation, persistence, capacity reservation or fleet-level enforcement. The architecture must preserve these distinctions.

## 2. Source inventory and observed responsibilities

| Source | Observed responsibility | What the source does not establish |
|---|---|---|
| `core/llm/agent.py` | LLM-backed primary/secondary agent metadata, model reasoning, prompt construction and self-knowledge hydration | Agent capability strings do not prove a provider is installed or authorize a real action |
| `core/llm/model_fabric_bridge.py` | Converts a prompt into a single-model, text-only `ModelRequest`; tools are explicitly empty | Tool calling, action authority, multi-model consensus or provider-side action execution |
| `core/llm/self_knowledge.py` | Bounded read-only system identity, architecture, capability, limitation and runtime context | A versioned signed system-manifest or proof that every prompt fact is current |
| `jarvis/providers/base.py` | Minimal `ModelProvider.generate(prompt)` protocol | Provider identity, structured response, cancellation, timeout, usage, cost, privacy, streaming or tool schema |
| `jarvis/context/authorized.py` | Source registration and callback-gated context acquisition | Tenant/data-class scopes, consent receipts, retention, source attestation, freshness, immutable evidence or redaction |
| `jarvis/observation/fabric.py` | Callback-gated observation reader and event wrapper | Sensor authenticity, monotonic event ordering, anti-replay, clock trust, data minimization or evidence signature |
| `jarvis/perception/audio.py` | Typed audio frame/wake event and deterministic clap-pattern detection | Microphone permission, secure capture, liveness, speaker identity, wake-event authorization or action dispatch |
| `core/user_understanding.py` | Explicit consent enum, bounded content, heuristic signal extraction and evidence IDs | Longitudinal consent ledger, tenant binding, correction/deletion lifecycle, calibrated inference or durable profile lineage |
| `core/cyber_range.py` | Synthetic sandbox targets, symbolic attack phases and bounded simulation | Real-target execution; the owner authorization record is not itself a cryptographic signature or remote policy decision |
| `core/device_fabric.py` | In-memory device registry and first-online-capability lookup | Device enrollment, hardware attestation, trust score, region/capacity-aware selection, lease or distributed consistency |
| `core/distributed.py` | In-memory node and encrypted-shard placement descriptors | Encryption-key custody, replication, consensus, failover, durability, consistency or shard movement |
| `ecosystem/global_scale.py` | In-memory region/cell selection, capacity accounting, bounded queue, traffic route and language context | Real cloud control plane, durable broker, atomic distributed reservations, autoscaling, telemetry or workload execution |
| `web/app.py` | FastAPI UI/API routes; gateway session and execution endpoints plus direct chat route | A single uniform authentication boundary for every route |
| `gateway/auth.py` / `gateway/server.py` | Bootstrap-token exchange, HMAC session token and gateway execution path | Durable session revocation, client-to-human principal binding, device proof, refresh rotation or route parity with direct chat |

The inventory is a source review, not a runtime test or a security certification.

## 3. Ingress and surface authority

### 3.1 Two distinct API paths

The inspected FastAPI surface contains:

- `POST /v1/session`: bootstrap token plus client ID, issuing a short-lived HMAC-signed session token.
- `POST /v1/execute`: requires a Bearer token and calls `NoryxGateway.execute`, which verifies the token before invoking `RuntimeAdapter`.
- `POST /api/chat`: creates a task and calls `OperationalNORYXRuntime.run_hypersynth` directly in the route handler.

The `/api/chat` handler does not itself invoke `SessionAuthority.verify` or the gateway execution method. The inspected module also does not show an authentication dependency attached to that route. This is a confirmed route-level divergence in the reviewed source, **not proof that a deployment has no upstream proxy, middleware or platform-level control**. The required architecture decision is to define one explicit ingress policy and enumerate every route's enforcement point. Upstream protection must be configuration-backed evidence, not an assumption.

### 3.2 Canonical ingress contract

Every external request should carry or resolve:

1. request ID and idempotency key;
2. authenticated principal and issuer chain;
3. tenant/workspace and data classification;
4. client/device/session identity with assurance level;
5. purpose, consent scope and requested operation;
6. policy version, authorization epoch and expiry;
7. correlation IDs for task, execution, action and audit;
8. bounded payload, rate/resource budget and deadline.

Ingress authenticates the caller; it does not automatically authorize every requested capability. Authorization must be evaluated against the resolved principal, tenant, target, action digest, resource scope and current policy epoch. Surface adapters must not invent principals from a client-supplied label.

### 3.3 Session lifecycle

The current session token has an expiry and nonce and is HMAC-signed, but the inspected `SessionAuthority` keeps no durable token registry or explicit revocation list. A stateless signature can prove token integrity and expiry, but immediate revocation requires a revocation epoch/list or short-lived credential plus online policy check. Bootstrap secret rotation, client re-enrollment, compromised-client containment and signing-key rollover need one lifecycle contract.

The client ID is a session subject label; it is not by itself a verified human, organization or hardware identity. The future authority graph must distinguish user, organization, workload, agent, device, browser installation, session and execution identities.

## 4. JARVIS context, observation and perception

### 4.1 Context acquisition

`AuthorizedContext` performs a callback check for a registered source ID and then returns a `ContextItem` with a string provenance label. The authorization callback is a useful seam, but the data contract does not yet express field-level scope, purpose, tenant, consent receipt, sensitivity, retention or evidence freshness.

Architecture requirement: each context source publishes a versioned manifest containing owner, issuer, allowed principal classes, data classification, purposes, scope, retention, freshness, redaction policy, evidence type and revocation behavior. Acquired context is an evidence object, not trusted merely because a reader callback returned it.

### 4.2 Observation event integrity

`ObservationFabric.observe` receives its timestamp from the caller and constructs a provenance string from the source ID. It has no visible monotonic clock, signature, sequence number, freshness window or anti-replay state. Therefore the timestamp and provenance are descriptive metadata, not authenticated sensor evidence.

The canonical observation envelope should bind source/device identity, capture time, monotonic sequence, payload digest, modality, consent/purpose, calibration/version, location precision policy, retention class and attestation chain. Missing clock trust or device attestation must lower the evidence assurance level rather than silently promote it.

### 4.3 Audio wake and action boundary

The clap detector emits a typed wake event from a deterministic pattern detector. The detector explicitly does not authorize actions. The Android bridge's frame callback is a capture adapter seam; it is not proof that Android microphone permissions, background execution, hardware privacy indicators or secure capture are implemented.

A wake event may request a bounded interaction session only. It cannot grant payment, unlock, surveillance, device-control or other privileged capabilities. Subsequent speech recognition, speaker verification (if ever used), intent resolution, policy evaluation and explicit confirmation are separate stages. Biometric voice identity must never be inferred from a clap pattern.

## 5. User-understanding and consent lifecycle

The source model has `DENIED`, `PRE_INTERACTION` and `CONTINUOUS` consent states and bounded user content/signals. It uses deterministic lexical matching and fixed heuristic confidence values (for example topic/tone/format signals). This is a transparent baseline, but the numeric confidence is a heuristic score, not a calibrated probability that a profile inference is true.

The current profile is not a full consent ledger: the inspected structures do not encode a durable consent receipt, policy version, collection purpose, source-by-source scope, expiry, correction request, deletion tombstone, tenant boundary or downstream propagation receipt. A profile identifier derived from signal values is not a stable user identity.

Canonical lifecycle requirements:

- consent is granular by purpose, source, modality, processing and retention;
- denial is the default for non-essential continuous collection;
- pre-interaction processing must have a narrow, disclosed purpose and no silent promotion to continuous monitoring;
- raw content, extracted signals and derived inferences have distinct retention/deletion rules;
- every inference carries source evidence, method/version, timestamp and uncertainty;
- user correction supersedes an inference without erasing audit obligations;
- deletion propagates to memory tiers, caches, embeddings, replicas, exports and derived profiles, with tombstones where required to prevent resurrection;
- tenant and user isolation are enforced before retrieval, not after prompt assembly;
- the user can inspect, correct, export and revoke applicable profile data.

No behavioral profiling or personalization signal may become an authorization input unless a separately approved policy explicitly defines that use.

## 6. Cyber range and MIRROR WORLD safety boundary

The inspected `CyberRange` uses synthetic targets restricted to the `sandbox` trust zone, symbolic techniques and bounded action counts. This is consistent with the intended simulation-first boundary. Its `OwnerAuthorization` record checks a matching principal ID, non-empty authorization ID and expiry, but does not verify a signature, issuer, target scope, action digest, policy epoch or revocation state in this module.

The architectural requirement is stronger than a local record check:

- every scenario has a signed world/scenario manifest and immutable synthetic target namespace;
- simulation actions are symbolic and cannot be routed to a real-world adapter;
- any Reality Bridge transition is a distinct privileged operation with explicit target ownership, scope, time window, action allowlist, risk classification, human approval where required and a separately issued authorization;
- evidence from simulated worlds is permanently labeled simulated and cannot be relabeled as real-world observation;
- calibration data, model version, assumptions, uncertainty and holdout contamination are recorded;
- destructive, exploitative or safety-critical experiments remain sandbox-only unless a lawful, authorized and independently reviewed real-world test protocol exists.

A local authorization object is not sufficient to cross the simulation/real boundary.

## 7. Device, edge/cloud and global-scale semantics

### 7.1 Device fabric

The current device registry returns the first online device exposing a capability. This is deterministic only with respect to insertion order and does not prove that the device is trusted, available, resident in an allowed jurisdiction or able to satisfy the requested resource envelope.

The canonical selector must filter by verified device identity, attestation freshness, policy epoch, tenant, capability version, privacy/data residency, health, measured capacity, power/thermal state, network quality and user policy. A selected device must receive a bounded lease and signed task envelope; revocation and disconnect behavior must be explicit.

### 7.2 Distributed topology and shard placement

The current topology records node roles and encrypted-shard descriptors. The `encrypted` boolean is a declaration, not cryptographic evidence. Placement does not establish key custody, replication factor, consistency, quorum, anti-rollback, backup, repair or deletion propagation.

The architecture must distinguish control-plane topology metadata from the actual data plane. Shard manifests must bind ciphertext digest, encryption suite/key ID, tenant, residency, replica set, epoch, retention, lineage and restore policy. Key custody remains separate from node ownership. A node cannot claim that a shard is safe solely because the descriptor says `encrypted=true`.

### 7.3 Global scale and queue

`ecosystem/global_scale.py` explicitly describes itself as control-plane primitives rather than a cloud provider, database, scheduler or network fabric. Region/cell registries and event queues are in-memory. Region selection checks declared health, capacity and residency; the global traffic router then selects a cell, but the selection path does not itself establish a durable reservation with the worker. `ElasticComputeFabric` accounts for capacity in memory. `EventFabric` removes drained items from its local queue.

The production architecture therefore needs a reservation protocol with lease ID, fencing token, capacity epoch, expiry, idempotent acquire/release and reconciliation. Durable queue semantics must define at-least-once/at-most-once delivery, deduplication, poison-message quarantine, retry budget, ordering scope, backpressure and dead-letter retention. No in-memory registry or queue is evidence of fleet-wide elasticity or global availability.

## 8. Model/provider contract and advertised capabilities

The JARVIS provider protocol is currently a single `generate(prompt)` method. The LLM bridge submits one text-only model request with no tools. Agent capability metadata includes domain labels such as payments and flights, but these labels do not establish a configured provider or authorize transactions. The architecture must distinguish:

- reasoning capability (model can produce a proposal);
- domain adapter availability (a provider can perform a typed operation);
- policy authorization (principal may request that operation);
- execution authority (runtime dispatches the signed action);
- result evidence (provider response and external receipt are verified).

A provider contract should include provider/model identity, API/schema version, streaming and cancellation semantics, deadline, retry/idempotency contract, usage and cost evidence, data residency, retention/training policy, secret reference, error taxonomy, health/circuit state and provenance. Structured tool calls must be parsed as untrusted proposals and routed through the canonical ActionGate; the model never becomes the action executor.

## 9. Cross-workstream decisions added

The following are open decisions, not accepted designs:

| ADR | Workstreams | Decision required |
|---|---|---|
| B63 | W01/W08/W09 | One canonical ingress/authentication policy across FastAPI, gateway, browser and future surfaces; upstream enforcement evidence |
| B64 | W01/W06/W08 | Canonical context/observation evidence envelope: principal, tenant, source, time, sequence, digest, consent, classification and provenance |
| B65 | W01/W08/W09 | Device enrollment, attestation, lease, revocation and hardware-backed identity lifecycle |
| B66 | W06/W07/W09 | Cryptographically verifiable CyberRange owner authorization and immutable simulation-to-real boundary |
| B67 | W05/W08/W11 | Global capacity reservation, fencing, durable queue and exactly-defined retry/delivery semantics |
| B68 | W01/W06/W12 | Consent receipt, derived-profile lineage, correction/deletion propagation and non-authority of personalization signals |
| B69 | W05/W09/W11 | Provider contract, measured usage/cost/latency, privacy/residency, tool proposal and idempotent execution semantics |

## 10. Updated workstream disposition

- **W01 Authority & identity:** source mapping expanded for session, context, device and consent; canonical principal graph, revocation and durable consent remain open.
- **W02 Runtime topology:** direct API route and gateway route divergence identified; one ingress/lifecycle owner remains open.
- **W05 Routing & resources:** device selection and global capacity reservation are only local/in-memory primitives; placement and lease contracts remain open.
- **W06 Semantics & evidence:** observation/context provenance and heuristic confidence limitations documented; canonical evidence envelope remains open.
- **W07 MIRROR WORLD:** synthetic cyber-range boundary confirmed; signed authorization, calibration and Reality Bridge gate remain open.
- **W08 Surfaces & distribution:** JARVIS context/audio and FastAPI ingress mapped; surface capture/identity/revocation parity remains open.
- **W09 Security & assurance:** callback authorization and HMAC session token are source-level controls; key lifecycle, route enforcement and sensor/device trust remain open.
- **W11 Performance & operations:** global-scale structures are local registries/queues, not production fleet orchestration; reservation, telemetry and SLO evidence remain open.
- **W03/W04/W10/W12:** no status upgrade is implied; they remain partial and continue in parallel under their existing source-reconciliation documents.

## 11. Architecture-only acceptance conditions before integration

Before any implementation begins, the architecture freeze package must define and cross-reference:

1. one ingress policy and an explicit route-by-route authentication matrix;
2. principal/tenant/device/session identity and revocation lifecycle;
3. context, observation, audio and user-profile evidence/consent contracts;
4. simulation/real-world separation and Reality Bridge authorization;
5. device/region/cell capacity lease and durable queue semantics;
6. provider capability vs domain adapter vs authorization vs execution distinctions;
7. data retention, correction, deletion, audit and restore propagation;
8. failure modes for stale observation, expired consent, revoked device, lost lease, duplicate delivery and uncertain external effects.

Until these contracts are reviewed alongside all other workstreams, architecture remains PARTIAL. No integration or comprehensive test campaign is implied by this source reconciliation.
