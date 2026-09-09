# NORYX7 — Current Operational State

Date: 2026-09-09
Branch: `integration-wave-8-model-fabric-authorization-2026-09-09` (Wave 8 prepared from main)

## Mission

NORYX7 is being integrated as a distributed agentic AI architecture, not as a simple chatbot. The architecture separates intelligence, planning, policy, authorization, capabilities, execution, verification, state, recovery and memory.

## Canonical architecture

USER / TEXT / VOICE / BROWSER / API
→ IDENTITY / SESSION
→ USER UNDERSTANDING
→ GLOBAL + LOCAL MEMORY
→ HYPERSYNTH
→ MODEL FABRIC
→ JARVIS / ORCHESTRATION
→ POLICY
→ AUTHORIZATION
→ CAPABILITY REGISTRY
→ TOOL EXECUTOR
→ RUNTIME ENGINE
→ VERIFICATION / ATTESTATION
→ STATE / AUDIT / RECOVERY
→ MEMORY
→ USER / TEXT / TTS

Not every request must traverse every subsystem; orchestration selects the required path while preserving the security and verification boundaries.

## Integrated boundaries

### Wave 4 — Web runtime unification

The active web surface routes execution through the canonical gateway/runtime path instead of directly invoking the runtime.

### Wave 5 — Canonical system fabric

`CanonicalSystemFabric` is shared by the operational runtime, gateway and JARVIS bridge. Gateway sessions are bound to global identity authorization; execution provenance is recorded through the global memory fabric using digests rather than raw payload persistence.

### Wave 6 — Android Browser enrollment

The Android Browser no longer ships a gateway bootstrap credential. Browser enrollment uses a dedicated server-side pairing secret (`NORYX_BROWSER_PAIRING_CODE`) and receives a normal short-lived gateway session. The resulting browser identity is bound into `CanonicalSystemFabric` with the `execute` capability only.

The pairing code is entered at runtime and is not persisted by the Android client. The server-side pairing secret must be configured in the deployment environment before browser enrollment can succeed.

### Wave 7 — Agent identity fabric binding

The canonical system fabric now has an explicit agent-identity binding contract. A well-formed `AgentIdentity` is mapped to a key-fingerprint-bound synthetic agent session and must hold an explicit capability before a protected agent execution path may proceed.

The JARVIS bridge binds and authorizes its execution principal through the canonical system fabric before RuntimeEngine dispatch, and re-checks the explicit `execute` capability at the execution boundary. This supplements, rather than replaces, the existing cryptographic `AuthorizationAuthority`, `ActionGate`, policy and security checks.

The binding is fail-closed and does not implicitly grant authority. Key replacement produces a distinct binding because the public-key fingerprint is part of the agent session identity.

### Wave 8 — Model Fabric authorization and provenance

The model dispatch boundary is now connected to the canonical system fabric. `OperationalNORYXRuntime` explicitly binds the primary and secondary LLM agent identities with `execute` plus `model:execute` before bringing the operational agent runtime online.

`ModelFabricBridge` requires the already-bound `model:execute` capability before calling `ModelFabric.execute()`. The bridge does not auto-grant or elevate privileges. Model execution provenance is recorded through `CanonicalSystemFabric.record_execution()` using request/result/model/runtime metadata; the global fabric stores only digests, not raw prompts or model output.

The existing `ModelFabric` runtime binding, request digest, result integrity/MAC checks and model capability filtering remain authoritative. Wave 8 adds the canonical cross-component authorization boundary without replacing those checks.

## Verified historically

### JARVIS vertical execution

A complete test using an explicit policy grant succeeded historically:

- JARVIS policy grant: PASS
- JARVIS execute: PASS
- recovery guard: PASS
- JARVIS runtime bridge: PASS
- RuntimeEngine: PASS
- shared capability registry: PASS
- ToolExecutor: PASS
- authorization: PASS
- verification: PASS
- state commit: PASS
- final state: `committed`

These results are historical and are not a fresh verification of the current Wave 8 branch.

### Policy security

Previously verified:

- deny-by-default: PASS
- explicit grant: PASS
- revoke: PASS
- revoked execution blocked: PASS
- revoked handler was not called: PASS
- principal isolation: PASS
- capability isolation: PASS
- target isolation: PASS

## Security principle

The security layer is intentionally fail-closed and deny-by-default. Do not weaken policy, bypass authorization, auto-grant capabilities, remove checks, or modify tests merely to make an integration test pass.

If a protected path rejects an operation, first determine whether the rejection is the intended contract or a genuine integration defect.

## Important implementation facts

- `core/tools.py` contains the canonical capability registry and ToolExecutor.
- JARVIS registry delegates to the canonical core registry.
- JARVIS native handlers keep the `handler(PlanStep) -> ActionResult` contract.
- Core ToolExecutor handlers use `handler(target, dict(parameters))`; the JARVIS registry adapter translates between these contracts.
- `core/actions.py` owns the canonical ActionGate/AuthorizationAuthority path.
- Do not call `ActionGate.authorize()` separately before an auth-required `authorize_and_execute()` path because that can consume a one-shot grant twice.
- RuntimeEngine receives the actual action payload from the bridge, not the JARVIS `ActionResult` wrapper.
- JARVIS StateStore requires `results` as a list at commit time.
- RecoveryController is implemented in `core/recovery.py`.
- `core/system_fabric.py` owns the cross-component system-fabric boundary and now exposes explicit agent identity binding/authorization.
- `ecosystem/global_fabric.py` owns the bounded global memory and identity/authorization indexes.
- `noryx7_runtime/model_fabric.py` owns provider-neutral model routing, runtime binding, request/result integrity and model capability filtering.
- `core/llm/model_fabric_bridge.py` is the canonical LLM-to-ModelFabric dispatch boundary.
- Android Browser v0.1 remains a separate WebView project; it does not embed HYPERSYNTH or the chatbot.

## Known-good integration commits

- `81b68c8` — Wave 4 web/runtime unification
- `f46904f` — Wave 5 canonical system fabric integration
- `b6808f4` — Wave 6 secure Android browser enrollment
- `1a20e44` — Wave 7 agent identity fabric integration

## Current verification status

Wave 8 implementation is prepared on the integration branch. Focused Wave 8 tests have been added but have not been executed in this environment, so no fresh PASS claim is made. Live Render verification is also not available from the current environment.

## Current rule

Continue integration by identifying the next real disconnected boundary, inspect its existing contract first, make the smallest necessary change, run a focused test when execution is available, then run the relevant regression suite. Never claim repository or deployment verification that has not actually occurred.
