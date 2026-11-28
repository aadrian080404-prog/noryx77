# NORYX7 — Tool Protocol, Provider Failover, Execution Trace and External Effect Reconciliation

**Review date:** 2026-11-24  
**Source snapshot:** `edf5ffe69642a41c0cfeacd3551abdb63f20acf2`  
**Scope:** read-only source reconciliation and architecture documentation. No runtime, tests, dependencies, workflows, deployment or frozen baseline modified.

## 1. Purpose and assurance boundary

This pass examines the seams between tool invocation, provider selection, HTTP transport, execution tracing, egress, offline delivery and evidence admission. These are cross-cutting seams used by W01–W12.

Terms used below:
- **contract exists:** a typed API or architecture document is present;
- **local source behavior:** behavior is visible in the inspected class;
- **enforced system guarantee:** requires all call paths and bypasses to be controlled;
- **verified operational assurance:** requires reproducible runtime/deployment evidence.

A local callback, hash chain, HTTPS URL, or bounded retry count does not by itself establish a system-wide guarantee.

## 2. Tool protocol: authorization and provenance are too narrow for a canonical action record

### 2.1 Observed source behavior

`core/tool_protocol.py` defines:
- `ToolSpec(name, version, capabilities, handler)`;
- `ToolResult(tool, success, value, error, provenance)`;
- a local `ToolRegistry` with duplicate-name rejection;
- `invoke(name, args, authorize=...)`, which looks up the tool, invokes a supplied authorization callback, then calls the handler.

The callback receives only `ToolSpec`. It does not receive a canonical authenticated principal, tenant, session/device, policy epoch, target, data classification, request/attempt ID, or risk context through this interface. The result provenance is a string `name@version`; it does not bind an immutable artifact digest, handler/build identity, input digest, output digest, execution identity, source identity or authorization decision receipt.

The registry is in-process. No durable versioned tool catalog, signer/qualification manifest, revocation epoch or distributed registry consistency is established by this class.

### 2.2 Required tool invocation contract

Every invocation should bind:
1. tool ID, semantic version, immutable artifact/build digest and capability manifest;
2. authenticated principal, tenant, issuer, session/device/workload and policy epoch;
3. operation/request/task/step/execution/attempt/dispatch IDs;
4. canonical target and allowed resource boundary;
5. input schema/version, data classification, consent/purpose and input digest;
6. authorization decision, policy version, scope, expiry and reviewer where required;
7. sandbox/runtime identity, resource budget and egress policy;
8. start/finish timestamps and cancellation/deadline;
9. output schema/version, output digest, provenance and verification status;
10. effect certainty, receipt, idempotency key and recovery/compensation state.

Tool selection or capability labels are never authorization. Authorization must be evaluated at the final dispatch boundary and bound to the exact action and target.

## 3. Provider failover: exception is not proof that the provider had no effect

### 3.1 Observed source behavior

`core/provider_resilience.py` selects providers through `ProviderRouter`, builds an `ExecutionFabric` action and retries another provider after generic exceptions. Policy denial is terminal, which is appropriate. However:
- the action ID is derived from principal, provider, capability and attempt ordinal; it does not include a caller-supplied durable operation ID or idempotency key;
- a new invocation can reuse the same identifiers for the same principal/provider/capability/attempt;
- generic exceptions are treated as grounds for provider exclusion/failover;
- the executor does not classify whether a timeout/connection failure occurred before dispatch, during dispatch, after remote commit or while receiving the response;
- the attempt record contains provider, ordinal, success and exception type, but no durable dispatch receipt, remote operation ID, effect certainty or reconciliation state.

A provider may commit a side effect and then lose the response. Failing over to a second provider can duplicate the operation. This is a design hazard to resolve in architecture before broadening retries.

### 3.2 Required provider state machine

`PROPOSED → AUTHORIZED → ADMITTED → INTENT_DURABLE → DISPATCHED →`
- `EFFECT_CONFIRMED`
- `EFFECT_REJECTED`
- `EFFECT_INDETERMINATE`

Then:
- `RECEIPT_VERIFIED`;
- `REMOTE_RECONCILED`;
- `RETRY_SAFE` only when no effect is proven or the remote system guarantees idempotency for the same key;
- `COMPENSATION_REQUIRED` where a confirmed effect must be reversed;
- `MANUAL_REVIEW` where certainty cannot be recovered.

The retry policy must be capability- and provider-specific. Read-only/idempotent queries, idempotent writes and non-idempotent writes need different retry semantics. A generic exception handler must not silently imply retry safety.

## 4. HTTP provider: useful transport controls, incomplete network and effect semantics

### 4.1 Observed source behavior

`core/http_provider.py`:
- validates HTTP/HTTPS endpoint syntax and rejects embedded URL credentials;
- requires HTTPS unless insecure HTTP is explicitly allowed;
- supports a timeout and maximum response byte count;
- reads API credentials from an environment variable;
- rejects redirects;
- sends JSON POST and requires a JSON response;
- maps transport/HTTP/response failures to sanitized exceptions.

This is a useful bounded transport adapter. It does not, by itself, prove:
- DNS resolution pinning or rebinding resistance;
- IP-range/private-network/metadata endpoint denial;
- socket-level egress enforcement across all transports;
- TLS peer identity policy beyond the supplied/default SSL context;
- provider-side idempotency or operation lookup;
- remote effect certainty after timeout or truncated/lost response;
- durable request/response receipt retention;
- response source authenticity or semantic validity.

The redirect handler blocks redirects, but endpoint policy still needs canonical hostname resolution, resolved-address checks, connection pinning and enforcement at the actual socket boundary. URL validation is not network isolation.

### 4.2 Provider qualification manifest

Each provider should have a versioned record for:
- legal/service identity and endpoint owner;
- allowed regions and data residency;
- transport/TLS trust policy and certificate lifecycle;
- approved capabilities and request/response schemas;
- data processing, retention and training-use constraints;
- supported idempotency semantics and operation-status lookup;
- timeout and failure certainty behavior;
- rate, cost, quota and availability limits;
- independent qualification evidence, expiry and revocation;
- fallback equivalence and prohibited failover combinations.

Fallback must not move sensitive data to a provider with weaker residency/privacy controls or substitute a semantically different capability without explicit policy.

## 5. Execution trace: tamper-evident in-memory chain is not durable audit

### 5.1 Observed source behavior

`core/execution_trace.py` maintains a per-execution in-memory sequence. Each event hashes a canonicalized payload digest, prior digest, sequence, event type and execution ID; `verify()` recomputes the chain.

This detects mutation/reordering of retained events within the current object. It does not establish:
- persistence across process restart;
- authenticated actor identity or signer non-repudiation;
- external anchoring of the head;
- trusted timestamp;
- event completeness (an event omitted before append cannot be detected);
- cross-process ordering or distributed sequence ownership;
- confidentiality of event payloads;
- retention, access control, deletion policy or incident response.

A hash chain is tamper-evident only relative to a retained trusted head. If the entire in-memory chain and head are replaced together, this class has no external root to detect it.

### 5.2 Unified event envelope

A canonical event envelope should include schema version, event ID, tenant/principal, issuer, service/device/workload, policy epoch, operation IDs, event time and trusted-ingest time, monotonic sequence, event type, input/output digests, source references, decision receipt, effect certainty, previous digest, signer/key ID and retention classification.

Durable audit architecture must specify append-only storage, external checkpoint custody, key rotation/revocation, trusted time, replication, restore, access review, legal hold and incident ownership.

## 6. Protocol and egress composition

Tool protocol, provider router, HTTP adapter, egress policy, secure channel and gateway session are separate abstractions. The architecture must define the order and ownership of:
1. parse and schema validation;
2. principal/session/tenant resolution;
3. target canonicalization and DNS resolution;
4. capability/purpose/data classification;
5. policy and human approval;
6. egress admission at socket/transport boundary;
7. durable intent and idempotency record;
8. dispatch and remote receipt capture;
9. response authenticity/schema/semantic validation;
10. durable trace/audit and memory admission.

No tool/provider callback may bypass this path through a direct handler, alternate transport or local adapter. A secure channel protects a channel under its trust assumptions; it does not automatically authorize the semantic operation.

## 7. Cross-workstream delta

| Workstream | Source reconciliation | Required architecture closure | Status |
|---|---|---|---|
| W01 Identity | Tool authorization callback receives ToolSpec, provider receives principal string; no canonical principal/session contract at these seams | Issuer/tenant/session/device context bound to each exact action | PARTIAL |
| W02 Runtime | Provider/tool attempts lack one durable operation/attempt/receipt lifecycle | Canonical operation IDs, intent, attempt, cancellation, effect and recovery state | PARTIAL |
| W03 Memory | Tool/provider provenance is a short label, not source-to-output lineage | Input/output artifacts, consent/purpose, retention and derived-memory lineage | PARTIAL |
| W04 Agent Fabric | Agent-selected tools/providers can enter separate local dispatch abstractions | One delegated capability and final ActionGate/dispatch authority | PARTIAL |
| W05 Routing | Provider failover is bounded but not effect-aware or residency/cost equivalent | Provider qualification, health/capacity, residency, semantic equivalence and retry safety | PARTIAL |
| W06 Evidence | Execution trace hashes event payloads but does not validate claim truth or source authenticity | Signed source/result receipts, claim lineage and independent semantic review | PARTIAL |
| W07 MIRROR WORLD | External provider/model calls can influence simulation inputs and parameters | Provider/model provenance, deterministic replay and model-version/evidence binding | PARTIAL |
| W08 Surfaces | Tool calls from gateway/device/browser need consistent session and idempotency context | Cross-surface request envelope and durable replay/receipt semantics | PARTIAL |
| W09 Security | HTTP URL/TLS/redirect controls do not prove DNS/socket egress or remote action authorization | Socket-level egress, provider trust, signed grants, durable replay and key lifecycle | PARTIAL |
| W10 Domains | Tool/provider version labels do not qualify specialist capability or validity | Qualified provider/tool manifests and domain-specific validation | PARTIAL |
| W11 Operations | Trace/attempt records are in-memory and not sufficient for recovery/incident audit | Durable telemetry/audit, provider SLOs, DR, cost/quota and incident workflows | PARTIAL |
| W12 Ecosystem | External provider side effects can include payments, procurement or project actions | Explicit consent, segregated funds, receipts, reconciliation and human governance | PARTIAL |

## 8. Decision mapping — consolidate existing ADRs

No duplicate ADR series is introduced. Extend or cross-reference:
- B70: durable security events, audit custody and incident lifecycle;
- B71/B96/B98: enforced egress, provider attestation and untrusted-content isolation;
- B72: tool/provider artifact and release provenance;
- B79/B80/B85/B86: principal context, operation identifiers, canonical dispatch and effect certainty;
- B87/B88: DAG execution and independent result admission;
- B90/B97: evidence assurance ladder and claim lineage;
- B95: provider/global-fabric adapter contract;
- B102: issuer/session/device trust;
- B104: durable intent, idempotency and uncertain side-effect reconciliation.

All remain OPEN/PROPOSED unless separately accepted. No decision is frozen by this source review.

## 9. Closure status

W01–W12 remain PARTIAL. This document specifies missing contracts and failure semantics; it does not implement provider idempotency, DNS pinning, durable trace, audit storage, remote receipts, socket mediation or integration. No test, CI, production-readiness or architecture-freeze claim is made.
