# NORYX7 — Polyglot surfaces, JARVIS authority and deployment reconciliation

**Inspected source ref:** `main` at `7d900bc75843ea968aa5886d251dbfac83a5d93c`  
**Status:** active architecture-only source reconciliation; not a production security assessment  
**Workstreams:** W01, W02, W03, W04, W05, W08, W09, W11, W12

## 1. Why this document is necessary

The repository is not a Python-only runtime. The root contains a Python gateway and web app, a Go gateway service, a Rust runtime library, a Swift iOS adapter, a Kotlin Android bridge, an Android browser, JARVIS Python runtime and TypeScript UI interaction surface. These pieces have different maturity and responsibility. They must be mapped as separate surfaces/services and not described collectively as one operational runtime.

## 2. JARVIS — actual composition and authority boundaries

### Direct source observations

`jarvis/core/runtime.py` constructs:
- JARVIS `Policy`, `AuditLog`, `JarvisStateStore` and `RecoveryController`;
- core `VerificationEngine`, `PolicyEngine`, `SecurityBoundary`, `RuntimeLimits`, `ActionGate`, `AuthorizationAuthority`, `ToolExecutor`, `IdentityRegistry`;
- a newly generated JARVIS agent identity and private key at runtime construction;
- `noryx7_runtime.engine.RuntimeEngine`;
- `CanonicalSystemFabric` and `JarvisRuntimeBridge`.

The bridge maps JARVIS plan steps into RuntimeEngine plan steps, checks JARVIS policy for each action, creates a core ActionSpec, issues canonical authorization, executes through the shared ToolExecutor, verifies the output and reconstructs JARVIS results.

JARVIS then verifies result count/order/success and commits a separate `JarvisStateStore` record. It has a JARVIS-specific audit log and bounded execution trace. `jarvis/core/recovery.py` re-exports the shared `core.recovery.RecoveryController`, avoiding a second recovery state machine.

### Architecture consequences

1. JARVIS is a surface/orchestration front that already delegates privileged execution into RuntimeEngine and the canonical ToolExecutor; it should not be designed as an independent action runtime.
2. JARVIS Policy and core PolicyEngine/ActionGate are layered checks with different identities and semantics. The user principal is checked by JARVIS Policy; the JARVIS agent identity and canonical authorization authority protect core action execution. Their grant lifecycles, revocation timing and audit correlation must be explicit.
3. JARVIS StateStore and RuntimeEngine StateJournal are distinct state records. The JARVIS state store reserves/commits request results, while RuntimeEngine journal records step attestations. The cross-store transaction is not automatically atomic.
4. A new JARVIS agent identity is generated when JarvisRuntime is constructed. Architecture must decide whether identity is process-ephemeral, durable service identity or workload identity, and how key persistence/rotation/recovery is handled.
5. JARVIS audit and core security event/audit channels must share correlation identifiers while retaining separate trust/retention purposes.

### Required closure evidence

- Exact principal/agent distinction and dual-policy evaluation order.
- Atomicity/saga semantics between JARVIS request reservation, RuntimeEngine step reservation, attestation journal and JARVIS final commit.
- Durable JARVIS workload identity and key custody lifecycle.
- Provider retry/failover authorization and idempotency composition.
- One documented path for every JARVIS tool, provider and front-end call.

## 3. Python gateway and hosted service

### Direct source observations

- `gateway/server.py` provides an HTTP API boundary with health, session creation and execution routes. Its docstring says production deployment must terminate TLS.
- `gateway/auth.py` implements bootstrap-token plus HMAC-signed short-lived session tokens; both bootstrap and signing secrets are mandatory.
- `gateway/runtime_adapter.py` translates an authenticated browser request into `OperationalNORYXRuntime`, bounds text input and uses client identity as task context.
- `web/app.py` is the web application entrypoint; `render.yaml` declares a Python web service using Uvicorn, health check `/health`, free plan, and environment-injected OpenRouter/gateway secrets.
- `noryx7_operational.py` builds OperationalNORYXRuntime with an OpenRouter model adapter, a ModelFabric, optional state journal path and task time limit.

### Architecture consequences

- Bootstrap-token provisioning, rotation, client enrollment, session revocation and signing-secret rotation require an explicit operator/security lifecycle.
- TLS termination, reverse-proxy trust, forwarded headers, origin/CORS, rate limits, request size, session storage, multi-instance consistency and secret exposure are part of the gateway architecture, not deployment afterthoughts.
- If multiple gateway instances run, session signing and revocation semantics must be consistent; local-only state cannot silently imply global session revocation.
- The gateway's client_id must be mapped to a verified principal, not treated as a trusted user identity solely because it is present in the request.
- The hosted model-provider key, model selection, provider failover, data egress and tenant boundaries must be explicit.

## 4. Go and Rust services — maturity boundary

### Go gateway

`services/jarvis-gateway-go/main.go` currently exposes:
- GET `/health`, returning service/runtime/policy status;
- POST `/digest`, reading a request body and returning its SHA-256 digest;
- an HTTP listener on port 8080.

This is a small health/digest service, not a replacement for the authenticated Python gateway or a full agent execution gateway. The architecture must label its role and trust boundary accurately.

### Rust runtime library

`services/jarvis-runtime-rs/src/lib.rs` defines an `ExecutionEnvelope`, canonical JSON serialization followed by SHA-256 digest, and a deny-by-default authorization helper. It does not currently establish a full runtime lifecycle, identity authority, signed authorization, dispatch adapter, journal or recovery system.

### Required polyglot contract

For each language service, define:
- canonical wire schema and version negotiation;
- canonicalization rules, encoding and digest domain separation;
- signature/authentication and principal binding (a digest is integrity metadata, not authentication);
- replay/idempotency and expiry;
- error/status taxonomy and retry safety;
- compatibility policy and generated contract fixtures;
- ownership of policy, state, identity, audit and telemetry.

No language-specific service may independently redefine the meaning of action, principal, execution, approval, provenance or policy epoch.

## 5. Android, iOS and Browser surfaces

### Android JARVIS bridge

`android/noryx7-jarvis-bridge` currently exposes an `AudioWakeBridge` interface with start/stop and PCM frame callback. Its source comment explicitly leaves Android permission/audio implementation to the client. Treat this as an interface contract, not a complete voice runtime.

### iOS adapter

The Swift `NoryxIOSPlatformAdapter` is an actor with local device ID, local capability grants/expiry, local action handlers, current epoch and bounded consumed-action ID set. Epoch rotation clears grants, handlers and consumed IDs. Action execution checks device ID, epoch, capability expiry, handler presence and replay ID before invoking the handler.

This is a local platform boundary. It does not itself establish signed grants, remote revocation, durable replay state, hardware attestation, canonical policy authority or cross-device synchronization. Clearing consumed IDs on epoch rotation is safe only when the new epoch and old-epoch rejection are cryptographically and durably authoritative.

### Android NORYX Browser

- The manifest requests INTERNET, disables cleartext traffic and Android backup, and exports the launcher activity.
- `NavigationPolicy` permits well-formed HTTPS main-frame URLs and rejects user-info.
- `NoryxGatewayClient` requires HTTPS outside debug builds, authenticates using bootstrap token/client ID, holds a session token in process memory, retries once after HTTP 401 and requires a completed response with valid verification metadata.
- The browser uses WebView and a dedicated gateway client.

Architecture questions:
- Where are bootstrap credentials provisioned and protected on-device?
- Is client ID cryptographically bound to device identity and user principal?
- What are certificate validation/pinning, proxy, redirect, DNS rebinding and WebView-origin rules?
- How are cookies, downloads, file access, permissions, external intents and local content isolated?
- How are sessions cleared on logout, account switch, device compromise and remote revocation?
- Which actions are browser-only versus NORYX privileged actions, and how are they bound to ActionGate?

### TypeScript UI

`ui/jarvis/interaction.ts` is a separate UI interaction surface. It must consume versioned contracts and cannot become an authorization or execution authority.

## 6. Deployment and service lifecycle

The repository root contains `render.yaml`, `web/app.py`, `gateway/`, `noryx7_operational.py`, Go/Rust services, Android/iOS adapters and CI workflows. Deployment architecture must therefore be multi-artifact and multi-environment.

Required inventory:
- service and artifact catalog (Python gateway, operational runtime, Go gateway, Rust library, browser APK, iOS package, Android bridge, UI);
- build provenance and signed release manifests for each artifact;
- environment-specific configuration and secret injection;
- staging/promotion/rollback and schema compatibility;
- health/readiness/liveness semantics and dependency health;
- scaling/instance coordination and durable session/replay state;
- logs/metrics/traces and privacy constraints;
- backup/restore, incident response and service decommission.

A single Render service definition does not describe deployment of every listed artifact.

## 7. New architecture decisions

| ID | Priority | Decision | Required closure evidence |
|---|---|---|---|
| ADR-B30 | B0 | JARVIS dual-policy and identity authority semantics | Principal vs JARVIS agent identity matrix, policy order, grant revocation and audit correlation |
| ADR-B31 | B0 | Cross-store JARVIS/RuntimeEngine transaction semantics | Request reservation, step reservation, attestation append and final commit saga/recovery contract |
| ADR-B32 | B1 | JARVIS workload identity/key lifecycle | Durable identity issuer, key custody, restart, rotation, revocation and recovery |
| ADR-B33 | B1 | Polyglot service maturity and canonical wire contracts | Explicit role/maturity matrix, shared schemas, digest/signature semantics and compatibility rules |
| ADR-B34 | B1 | Mobile/browser device trust and bootstrap credential lifecycle | Device enrollment, secret storage, session revocation, hardware trust and platform capability boundary |
| ADR-B35 | B1 | Multi-artifact deployment and release authority | Artifact catalog, build provenance, signed promotion, environment secrets, rollback, observability and DR |

## 8. Workstream impact

- W01: gateway client_id, JARVIS user principal, JARVIS agent identity and iOS device identity must map to one principal/device/workload taxonomy.
- W02: JARVIS runtime already composes RuntimeEngine/SystemFabric/Bridge; the actual production entrypoint graph must be reconciled with the proposed SRC.
- W03: JARVIS request state, RuntimeEngine step journal and core state journal are distinct; cross-store commit/recovery is unresolved.
- W04: JARVIS front-end, orchestrator, capability registry, agent/provider adapters and operational agent fabric require one invocation/ownership map.
- W05: provider gateway/resilience and Go/Rust service boundaries require composed retry, digest and action dispatch semantics.
- W08: Browser, Android audio, iOS local action adapter and TypeScript UI require versioned surface contracts and session/device lifecycle.
- W09: gateway HMAC session secret, JARVIS workload signing key, device grants, TLS and artifact signatures require a single trust model with separate key purposes.
- W11: Render service, Python runtime, Go/Rust artifacts and mobile packages require an explicit release/deployment/operations architecture.
- W12: account/client enrollment, provider onboarding, tenant identity, billing and support cannot be inferred from the gateway session model.

## 9. Scope and next step

Inspected sources: `jarvis/core/runtime.py`, `jarvis/core/orchestrator.py`, `jarvis/core/policy.py`, `jarvis/core/state.py`, `jarvis/security/authorization.py`, `jarvis/security/audit.py`, `jarvis/tools/registry.py`, `core/jarvis_runtime_bridge.py`, `gateway/server.py`, `gateway/auth.py`, `gateway/runtime_adapter.py`, `services/jarvis-gateway-go/main.go`, `services/jarvis-runtime-rs/src/lib.rs`, `ios/NoryxIOSAdapter`, `android/noryx7-jarvis-bridge`, `noryx-browser`, `ui/jarvis/interaction.ts`, `render.yaml` and `noryx7_operational.py`.

This is a bounded source reconciliation. The complete endpoint, caller, platform permission, secret-provisioning and release pipeline inventories remain open. No code, dependencies, tests, integration or deployment were changed.
