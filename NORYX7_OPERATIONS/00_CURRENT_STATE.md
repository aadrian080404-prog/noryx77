# NORYX7 — Current Operational State

Date: 2026-09-10
Branch baseline: `main`; Wave 10 is prepared on `integration-wave-10-end-to-end-closure-2026-09-10`.

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

Not every request must traverse every subsystem; orchestration selects the required path while preserving security and verification boundaries.

## Integrated boundaries

### Wave 4 — Web runtime unification

The active web surface routes execution through the canonical gateway/runtime path instead of directly invoking the runtime.

### Wave 5 — Canonical system fabric

`CanonicalSystemFabric` is shared by the operational runtime, gateway and JARVIS bridge. Gateway sessions are bound to global identity authorization; execution provenance is recorded through the global memory fabric using digests rather than raw payload persistence.

### Wave 6 — Android Browser enrollment

The Android Browser no longer ships a gateway bootstrap credential. Browser enrollment uses a dedicated server-side pairing secret (`NORYX_BROWSER_PAIRING_CODE`) and receives a normal short-lived gateway session. The resulting browser identity is bound into `CanonicalSystemFabric` with the `execute` capability only.

### Wave 7 — Agent identity fabric binding

The canonical system fabric has an explicit agent-identity binding contract. A well-formed `AgentIdentity` is mapped to a key-fingerprint-bound synthetic agent session and must hold an explicit capability before a protected agent execution path may proceed.

### Wave 8 — Model fabric and operational collaboration

Primary and Secondary agents are backed by the canonical `ModelFabric`; operational collaboration is verified through Primary → Secondary → Primary and fabric dispatch/admission audit events.

### Wave 9 — Runtime/system-fabric boundary

The canonical system fabric is the intended shared authority boundary for operational runtime, gateway and JARVIS. The remaining question was whether a real HYPERSYNTH lifecycle actually traversed that fabric rather than merely exposing the object.

### Wave 10 — End-to-end closure audit and lifecycle binding

The audit found two concrete closure gaps:

1. The operational runtime exposed `system_fabric`, but direct `run_hypersynth()` execution did not itself record canonical lifecycle provenance.
2. The hosted web runtime constructed an operational runtime independently of the configurable task-timeout and user-understanding integration used by the operational entrypoint.

Wave 10 addresses those boundaries together:

- operational lifecycle records canonical `runtime_received`, `runtime_committed` or `runtime_rejected` provenance through the same `CanonicalSystemFabric`;
- gateway execution and direct runtime execution can now be checked as one continuous lifecycle;
- hosted web runtime uses `NORYX7_MAX_TASK_SECONDS` through `RuntimeLimits`;
- hosted web runtime configures consent-bound `UserUnderstandingEngine` for first-interaction context derivation;
- dedicated closure tests verify direct runtime provenance and gateway → runtime → committed → gateway lifecycle records.

## Audit findings that remain important

- The JARVIS execution plane is intentionally optional and fail-closed until explicitly configured with its runtime engine, authorization authority, principal and policy.
- Voice has a canonical `VoiceGateway` and verified runtime boundary, but the active hosted web surface does not currently expose microphone/STT/TTS endpoints. This is an interface integration boundary, not a hidden claim of live voice availability.
- External providers such as payments, flights and insurance remain fail-closed until real provider adapters and credentials are configured.
- A green unit/integration suite is not equivalent to a live Render deployment verification. Deployment configuration and real provider credentials must be checked separately.

## Security principle

The security layer is intentionally fail-closed and deny-by-default. Do not weaken policy, bypass authorization, auto-grant capabilities, remove checks, or modify tests merely to make an integration test pass.

## Current rule

Work in waves of 3–4 real boundaries:

1. inspect for disconnected or false integrations;
2. integrate the boundaries together;
3. run focused closure tests;
4. run the full regression suite;
5. perform a real end-to-end execution where credentials/environment permit it.

Never claim that every component is live merely because it exists in the repository.
