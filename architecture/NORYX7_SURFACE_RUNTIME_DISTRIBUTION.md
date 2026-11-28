# NORYX7 — Surface, Runtime and Distribution Architecture

**Status:** architecture-only specification; no interface integration is claimed  
**Scope:** JARVIS, NORYX Browser, orchestration, APIs, device/edge/cloud/offline, terminal and operational lifecycle.

## 1. Product separation and surface topology

NORYX7 exposes distinct surfaces with separate release, trust and lifecycle boundaries:

| Surface | Product role | Explicit non-goal / boundary |
|---|---|---|
| JARVIS | Assistant and workflow front-end | Not a root authority or unrestricted host agent |
| NORYX Browser v0.1 | Standalone Android WebView browser | No HYPERSYNTH, chatbot, AI, cloud account, telemetry or implicit browser-to-agent bridge |
| NORYX7 API | Programmatic task and event ingress | No bypass of identity, policy, rate limits or schema validation |
| Operator console | Administrative visibility and approved control workflows | No model-driven privilege escalation |
| Device client | Local user interaction and device capability requests | Device permissions remain explicit and OS-bound |
| Edge node | Local compute, storage, gateway and verification placement | Node compromise must not expose global trust roots |
| Cloud runtime | Elastic compute and remote adapters | Cloud is a placement target, not the sole authority or mandatory dependency |
| Offline runtime | Explicitly scoped local execution | No silent cloud fallback; stale revocation state limits allowed actions |
| Terminal | Bounded developer/operator execution environment | Shell access is not ambient NORYX7 authority |

## 2. JARVIS front architecture

JARVIS owns the conversational/workflow lifecycle:
- session and interaction state;
- voice/text perception adapters;
- intent and plan proposal;
- bounded context assembly;
- policy/capability request formation;
- presentation of confirmation requests;
- result rendering and follow-up state.

JARVIS does not own:
- root identity or key custody;
- policy truth;
- capability issuance;
- trusted state commit;
- unrestricted tool execution;
- Browser v0.1 internal implementation.

The JARVIS flow is:

`SURFACE INPUT → SESSION BINDING → IDENTITY CONTEXT → INTENT/PLAN PROPOSAL → POLICY/CAPABILITY REQUEST → RUNTIME DISPATCH → RESULT VERIFICATION → PRESENTATION → AUDIT`

JARVIS may call providers only through registered provider adapters. Provider output is untrusted. User-visible summaries must distinguish completed, partial, rejected and failed operations.

## 3. NORYX Browser v0.1 and future bridge

Browser v0.1 is architecturally isolated as a standalone Kotlin/XML/ViewBinding/WebView product. Its current declared baseline remains the authority for v0.1.

Future integration is a separately versioned optional bridge:
- Browser produces a navigation/action request with URL, tab/session reference and user gesture.
- Bridge binds the request to the authenticated user/session and current navigation state.
- Policy classifies the requested operation and any sensitive content access.
- Capability grant scopes the exact operation, target, expiry and data exposure.
- Browser remains the renderer and navigation owner; NORYX7/JARVIS handles only explicitly delegated workflows.
- Results return as typed status and provenance references, not as hidden JavaScript privilege.

Bridge invariants:
- no JavaScript bridge into privileged NORYX7 APIs;
- no arbitrary DOM extraction or cookie/session export;
- no background browsing without explicit user intent and policy;
- origin, redirect, download, upload, file chooser and external intent policies are explicit;
- prompt injection and hostile page content are untrusted data;
- user confirmation binds to the exact action/target and expires on material change;
- Browser v0.1 remains unchanged unless a separately reviewed product decision authorizes a new version.

## 4. Orchestration lifecycle

Orchestration coordinates, but does not own authority:
`RECEIVED → UNDERSTOOD → PLANNED → ADMITTED → RUNNING → VERIFYING → COMMITTED → PRESENTED`

Alternative terminal states: rejected, incomplete, cancelled, expired, failed, quarantined, degraded.

The orchestration envelope carries IDs, typed references, digests, policy snapshot reference, budget and lifecycle state. It should not duplicate raw content, private credentials or capability authority.

Transitions require:
- authenticated actor;
- valid prior state;
- monotonic event sequence;
- expected state version;
- deadline/cancellation check;
- explicit reason for exceptional transitions.

## 5. Device / Edge / Cloud / Offline placement

### Device
- user-controlled interface, local secure storage and device-bound capabilities;
- OS permission and keystore integration;
- explicit local data classification and sync policy.

### Edge
- local inference/preprocessing, sensor gateway, cache, policy enforcement and bounded services;
- per-node identity and attestation;
- segmented management/data networks;
- signed workloads and encrypted persistent storage.

### Cloud
- elastic compute and managed adapters;
- tenant-isolated execution and storage;
- explicit data residency, egress and key custody policy;
- no assumption that cloud provider identity equals NORYX7 user authority.

### Offline
- local-only workloads with explicit offline policy snapshot and expiry;
- revocation epoch/freshness requirements;
- restricted high-impact or irreversible actions when revocation cannot be checked;
- signed synchronization proposals and conflict reconciliation;
- no implicit route to cloud.

Placement decision inputs include latency, privacy, residency, model/tool availability, trust posture, energy/cost and failure domain. A placement optimization cannot override a security or user-consent requirement.

## 6. Terminal and developer environment

The terminal is an execution adapter with session identity, shell type, working directory, scoped capabilities, resource budget, egress policy, deadline and audit stream.

Modes:
- ephemeral isolated shell;
- persistent workspace with separately authorized storage;
- local terminal;
- cloud terminal;
- remote job through attested endpoint.

Command execution contract:
`PARSE → CLASSIFY → AUTHORIZE → SANDBOX → EXECUTE → CAPTURE → VERIFY → AUDIT`

Shell metacharacters, scripts and child processes are not separate authorization channels. Unknown commands, privilege changes and egress are denied unless explicitly permitted. Secrets are injected through scoped secret providers, never placed into ordinary model context.

## 7. Cross-surface identity and session model

- identity principal is distinct from surface session and device identity;
- sessions have unique IDs, expiry, rotation and revocation;
- delegated work binds to originating principal and exact request;
- device replacement or session restore requires reauthentication and key lifecycle checks;
- cross-surface continuation carries references/digests, not transferable bearer authority;
- confirmation is action-specific and invalidated by target/scope changes.

## 8. Accessibility, localization and human factors

Every surface must define:
- keyboard/screen-reader and assistive technology semantics;
- clear permission and confirmation presentation;
- uncertainty, source and failure display;
- safe interruption and cancellation;
- language/locale and unit handling;
- prevention of deceptive or coercive consent patterns;
- recoverable workflows after connectivity loss.

## 9. Operational service objectives

SLOs must be set by workload class, not one global latency promise:
- interactive informational tasks;
- long-running research and analysis;
- external side-effect workflows;
- offline tasks;
- high-risk approvals;
- recovery and emergency containment.

Each SLO specifies percentile, measurement boundary, load profile, region/device class, dependency assumptions and allowed degraded mode. No latency target can bypass verification.

## 10. Architecture acceptance criteria for later integration

- Browser v0.1 remains isolated from JARVIS/HYPERSYNTH unless new version approved.
- Every surface session binds to identity, expiry and revocation.
- No surface grants capabilities.
- No untrusted page/provider/model output becomes executable instruction.
- Device/edge/cloud/offline placement preserves tenant, key, provenance and revocation boundaries.
- Offline mode never silently falls back to cloud.
- Terminal commands run only in bounded sandboxes with explicit capabilities.
- User confirmation binds to exact action digest and target.
- Cancellation, failure and partial completion are represented consistently.
- Accessibility and safe recovery are tested for each surface.

