# NORYX7 — Disconnected-by-Default Network Presence, Access Leases and Egress Architecture

**Review date:** 2026-11-27  
**Reviewed branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source-tree HEAD:** `8a2bdafda79c03950ee52cbbe07296f2a01da6a6`  
**Mode:** architecture-only source reconciliation and proposed cross-stream contract. No runtime, browser, device, test, dependency, workflow, deployment, frozen baseline or production configuration changed.

## 1. Executive principle

NORYX7 should not equate device power-on, user presence, local computation and Internet reachability.

The target security posture is **disconnected by default, connected by explicit short-lived purpose-bound lease**:

- Local device and local NORYX7 capabilities remain available without external network access where the device and offline policy permit them.
- Outbound network access is denied unless a named workload has a valid lease for a specific purpose, destination, protocol, data class and time window.
- Background processes do not retain indefinite network authority merely because the device is powered on or a user once authenticated.
- When the lease expires, is revoked, the app leaves an authorized foreground state, or policy/identity freshness is lost, the mediated path closes and queued work remains local.
- Inbound reachability is separately denied by default. A client device should not become an exposed server merely because it can initiate an outbound session.
- Physical radio control is a separate platform capability. NORYX7 must not claim it can switch Wi-Fi/cellular hardware off on every ordinary Android device or from an ordinary app process.

The goal is not to promise that the Internet itself is globally switched off. It is to minimize NORYX7's externally reachable and externally communicating attack surface, with user-controlled device-level radio settings as an optional additional layer.

## 2. Source-backed current-state observations

Source-tree HEAD inspected: `8a2bdafda79c03950ee52cbbe07296f2a01da6a6`.

### 2.1 Existing controls worth preserving

- `core/egress.py` provides an in-memory allowlist keyed by component, canonicalized host, port and protocol. Unlisted requests are denied; rules can be revoked. This is a useful policy primitive, not an OS-enforced network boundary.
- `core/device.py` defines device trust, audience-bound capability grants, expiry and policy epoch checks. The gate is local/in-memory and does not itself enforce radio state or intercept all sockets.
- `core/device_fabric.py` tracks registered devices and an online boolean in a process-local map. Online status is registry metadata, not proof of actual network reachability or device attestation.
- `core/offline.py` defines offline states, signed/authenticated snapshot hook, offline capabilities, encrypted outbox and reconnect flow. Its queue and sequence are in-memory in the inspected implementation; an acknowledgement/removal is not a durable remote commit receipt.
- `noryx-browser/app/src/main/AndroidManifest.xml` statically declares `android.permission.INTERNET`; cleartext traffic is disabled and backup is disabled. The INTERNET permission is not a per-session toggle.
- `NavigationPolicy.kt` permits well-formed HTTPS main-frame URLs without userinfo. `NoryxWebViewClient.kt` applies that policy to main-frame navigation callbacks, but permits non-main-frame resource requests through WebView.
- `NoryxGatewayClient.kt` performs direct `HttpURLConnection` requests for session creation and execution. It stores a bearer session token in memory, authenticates lazily and retries once after HTTP 401. It has a manual `clearSession()` method; the inspected `MainActivity` does not bind it to a short-lived network-presence lease or explicitly clear it on app background/idle transitions.
- Browser navigation and gateway transport therefore have different paths. The inspected browser client does not route every WebView subresource and every direct gateway socket through the Python `core/egress.py` policy.

### 2.2 What these observations do not prove

They do not prove that the deployed Android application is currently exploitable, that other OS/network controls are absent, or that every network path in the full deployment bypasses a gateway. The findings are bounded to the named source files and source snapshot. A source-level allowlist is not a packet filter; an HTTPS URL policy is not destination authorization; a local online flag is not an authenticated connectivity state.

## 3. Separate the five network states

Do not compress connectivity into one boolean such as `online`.

1. **Device power state** — powered, suspended, locked, shutting down.
2. **Radio/link state** — Wi-Fi, cellular, Ethernet, Bluetooth PAN or other bearer enabled/disabled/connected.
3. **Internet reachability** — a route and resolver exist; this is observed, not assumed.
4. **NORYX7 network authority** — the specific workload currently holds a valid network lease.
5. **Application session state** — foreground, background, idle, locked, expired or explicitly disconnected.

A device may have an active radio but no NORYX7 egress authority. NORYX7 may be locally usable while the device is disconnected. A user may intentionally enable the network while a specific NORYX7 component remains denied.

## 4. Canonical NetworkAccessLease contract

Proposed typed record, not implemented:

`NetworkAccessLease` should bind:

- lease ID, schema/version, issuer, audience and policy epoch;
- authenticated principal, tenant, enrolled device/workload identity and device trust evidence;
- initiating user action and declared purpose;
- permitted component/service identity and operation class;
- exact hostname/service identity, port, protocol and allowed HTTP methods where applicable;
- DNS answer set, resolution time, TTL, address classification and connection binding policy;
- TLS peer identity/certificate validation policy and optional pin-set version;
- redirect policy: disabled by default or reauthorize every hop and resolved destination;
- data classification, consent purpose, allowed request fields and maximum outbound bytes;
- rate, concurrency, request count, duration and cost budgets;
- foreground/background policy, user-presence requirement and idle timeout;
- offline snapshot/version and maximum staleness where offline transition is allowed;
- issue time, not-before, expiry, revocation sequence and one-use/reusable semantics;
- audit correlation, evidence references and revocation reason.

A lease grants permission to attempt a narrowly scoped network operation. It does not prove that the remote party is trustworthy, that the request succeeded, or that an external side effect committed.

### 4.1 Lease lifecycle

`REQUESTED → POLICY_EVALUATION → USER_CONFIRMATION (if required) → ISSUED → ACTIVE → CLOSED / EXPIRED / REVOKED / DENIED`

Additional state:
- `SUSPENDED` when the app loses required foreground/user-presence conditions or device trust becomes uncertain;
- `RECONCILIATION_REQUIRED` when an in-flight non-idempotent request may have reached the remote service but the response is lost;
- `QUARANTINED` when destination identity, DNS, TLS or policy changes unexpectedly.

The lease must be revoked on logout, principal/device revocation, policy epoch change, lock/idle threshold where required, app process death, explicit disconnect, destination policy update or incident containment. A new session requires a fresh decision; do not silently resurrect expired authority from a cached bearer token.

## 5. Network-presence modes

Define explicit user-visible modes. Defaults must be conservative and must not hide a connected background state.

| Mode | Local capabilities | Outbound NORYX7 access | Background sync |
|---|---|---|---|
| DISCONNECTED | Local/offline-approved functions | Denied | Queued locally |
| ON_DEMAND | Local functions | One short-lived lease per approved task | Denied |
| ACTIVE_SESSION | Local plus selected remote functions | Only listed services and operations | Limited to session scope |
| MAINTENANCE | Diagnostics/update only | Signed update/health endpoints only | Restricted and auditable |
| INCIDENT_LOCKDOWN | Safe local read-only functions | Denied except separately authorized recovery channel | Denied |

No general-purpose `always connected` mode should be silently enabled by a convenience setting. If a user explicitly enables persistent connectivity for a required service, show its purpose, destinations, expiry/renewal behavior and data categories.

## 6. Platform enforcement: app policy is not radio control

The architecture must implement defense in depth and accurately describe platform limits:

1. **NORYX7 application gate:** no network client is constructed or invoked without a valid lease.
2. **Central egress broker:** all NORYX7 service requests pass through one policy-enforcing broker or a small number of explicitly inventoried transports.
3. **OS-level enforcement:** use supported per-app firewall/VPN/device-owner controls where available; verify coverage for IPv4, IPv6, DNS, UDP/QUIC, proxy and background services.
4. **User-controlled radio state:** where ordinary app privileges cannot toggle Wi-Fi/cellular, present instructions or hand off to system settings; do not claim a programmatic radio-off guarantee.
5. **Hardware/enterprise deployment:** only a privileged, managed-device or firmware-integrated build may claim stronger radio control, and only after platform-specific validation.
6. **Server-side egress:** gateway/runtime workloads use deny-by-default network policy independent of client-side controls. Client leases cannot authorize arbitrary server egress.

An Android INTERNET manifest permission is static package capability, not a dynamic switch. A VPN/firewall can mediate app traffic without necessarily turning off the device radio. Airplane mode or radio shutdown affects other applications and emergency communications, so any device-wide change remains a user/platform-controlled operation with explicit confirmation and safety exceptions.

## 7. Required transport mediation and bypass inventory

Every network-capable path must be catalogued and mediated:

- WebView main-frame navigation;
- WebView subresources, service workers, downloads, WebSockets and media;
- direct HTTP clients such as `HttpURLConnection`, OkHttp or platform SDKs;
- DNS resolution, DoH/DoT, proxies, QUIC/UDP and IPv6;
- model/provider APIs, research/search tools and plugin connectors;
- telemetry, crash reporting, analytics and update checks;
- push notifications and background jobs;
- child processes, native libraries and embedded runtimes;
- local network discovery, mDNS, Bluetooth PAN and peer-to-peer paths;
- edge/cloud service egress and third-party callbacks.

For the Android browser specifically, the architecture needs a decision on whether WebView is allowed direct public browsing. If yes, its subresources, redirects, downloads, WebSockets and DNS destinations need policy enforcement. If no, it must use a controlled proxy/browser network service with explicit origin and content policies. A main-frame URL check alone cannot enforce the full page's network behavior.

The gateway client should use a lease-aware transport interface. Its session token must be scoped to the authenticated device/principal, purpose, server audience, policy epoch and short expiry. Clear the token and cancel pending work on disconnect, lock/idle policy, logout, device revocation and process teardown. A 401 retry may obtain a new session only if the original lease remains valid and policy explicitly allows reauthentication.

## 8. Offline and reconnection protocol

Disconnected mode is a first-class operating state, not an error page.

- Local computation, cached knowledge and user-authorized offline workflows continue only within a signed, bounded offline capability snapshot.
- Sensitive/high-impact actions requiring fresh remote authorization remain unavailable offline.
- Offline writes are queued with unique operation ID, principal/device binding, base-state version, policy epoch, payload digest, expiry and encrypted payload.
- The outbox must become durable before any user-visible promise that an operation is safely queued.
- On reconnect, authenticate device and user, check revocation/policy freshness, then submit a signed sync manifest.
- The server returns a signed receipt for each accepted/rejected/reconciled operation, binding operation ID, payload digest, server sequence and resulting state version.
- Remove an outbox item only after the matching authenticated remote commit/rejection receipt is durably stored locally.
- If the remote effect is ambiguous, quarantine and reconcile by idempotency key. Never blindly replay a payment, message, publication, device command or other non-idempotent operation.
- Conflicts preserve both versions and provenance; do not silently overwrite user data.
- Expired snapshots transition to read-only/local-safe mode until refreshed.

## 9. Threat model and containment

| Threat | Required control |
|---|---|
| Malicious or compromised page | Main-frame and subresource policy, origin isolation, downloads/content restrictions, browser sandbox |
| DNS rebinding / CNAME change | Resolve and classify addresses at connection time; bind allowed resolution and revalidate redirects |
| Redirect to private/metadata endpoint | Reauthorize each redirect and resolved IP; deny loopback/private/link-local/metadata destinations unless explicit local policy |
| Stolen bearer token | Short TTL, device/audience/purpose binding, server revocation, memory minimization, clear on idle/disconnect |
| Background task silently reconnects | Central transport gate plus OS background-job policy; no lease, no network |
| Direct socket bypasses egress broker | OS/container policy and exhaustive socket/SDK/native-path inventory |
| Malicious local network | No trust based solely on LAN presence; authenticated peer identity and explicit service capability |
| Offline replay/rollback | Signed snapshot, anti-rollback anchor, unique operation IDs, durable outbox and server idempotency |
| Compromised gateway/provider | Data minimization, destination allowlist, independent receipt validation, bounded credentials and incident revocation |
| Connectivity flapping | State machine, backoff, no duplicate side effects, explicit unknown-outcome reconciliation |

Containment should be local-first: revoke the affected lease, cancel in-flight cancellable requests, block new egress, preserve encrypted pending work and record an incident event. Do not erase evidence or assume cancellation reverses a remote effect.

## 10. Cross-stream ownership and dependencies

| Stream | Required responsibility |
|---|---|
| W01 Identity/Trust | Authenticate principal, tenant, device/workload and issuer; bind lease audience and revocation |
| W02 Runtime/Orchestration | Require lease before dispatch; bind network attempt to operation/attempt IDs and unknown-effect state |
| W03 Memory/State | Store durable encrypted outbox, lease/audit records, revocation and reconciliation checkpoints |
| W04 Agent Fabric | Agents may request connectivity but cannot mint leases or expand destination scope |
| W05 Routing/Providers | Route only to lease-authorized providers; enforce destination, cost, rate and idempotency |
| W06 NEXUS/FRL | Treat acquired network content as untrusted evidence until source custody and claim admission succeed |
| W07 MIRROR WORLD | Simulated connectivity and cyber-range results remain separate from real network observations |
| W08 Browser/Device/Offline | Present explicit connection modes, lease lifecycle, disconnect UX and offline-first continuity |
| W09 Security/Crypto/Audit | Sign/verify leases and receipts, rotate/revoke keys, persist tamper-evident network audit and incident controls |
| W10 Specialist Intelligence | External domain calls require explicit purpose, qualification scope and data minimization |
| W11 Global Operations | Enforce per-region/per-workload egress, lease revocation propagation, network segmentation and failure-domain policy |
| W12 Economy/Governance | Network usage budgets and paid-provider spend require treasury authorization; governance cannot override security egress deny rules |

## 11. Proposed acceptance gates (future integration and validation phase)

No tests were run in this architecture-only pass. When the architecture is closed and integration is authorized, validate at least:

1. No NORYX7 network-capable code path can send traffic without a valid lease.
2. Expired, revoked, wrong-device, wrong-principal, wrong-purpose, wrong-host, wrong-port, wrong-protocol and wrong-policy-epoch leases fail closed.
3. DNS rebinding, CNAME changes, IPv4/IPv6 alternate paths, redirect chains, proxy changes and private/metadata IP targets cannot bypass policy.
4. WebView subresources, WebSockets, downloads, service workers and direct gateway calls obey the same declared policy.
5. Background/idle/locked/disconnected app states do not silently reauthenticate or reconnect.
6. Lease expiry cancels or bounds in-flight work and records uncertain remote outcomes.
7. Process death, reboot, clock rollback and offline snapshot expiry cannot resurrect a lease or replay a committed operation.
8. Outbox survives process restart and only deletes records after authenticated matching server receipts.
9. Emergency recovery paths are narrowly scoped, time-limited, independently audited and cannot reopen general Internet access.
10. User radio controls and app-level egress controls are separately represented and tested on each supported Android version/device-management mode.
11. Server-side workloads cannot use client-originated lease claims as authority for their own arbitrary egress.
12. Network budgets, provider spend and privacy/data residency controls remain enforced under retries and failover.

## 12. New bounded closure gaps

- `GAP-W08-DEFAULT-DENY-NETWORK-PRESENCE-LEASE`: no canonical, purpose-bound, short-lived network lease and explicit disconnected/on-demand/session/maintenance/lockdown state machine across NORYX7 surfaces.
- `GAP-W08-ANDROID-PER-APP-RADIO-REALITY-BOUNDARY`: app-level network denial, OS/VPN/device-owner enforcement and physical radio control are not yet modeled as distinct platform capabilities with truthful guarantees.
- `GAP-W08-WEBVIEW-SUBRESOURCE-AND-DIRECT-TRANSPORT-MEDIATION`: main-frame HTTPS policy and gateway direct HTTP transport do not by themselves mediate all subresources, redirects, WebSockets, downloads, DNS and socket paths.
- `GAP-W08-SESSION-AND-BACKGROUND-RECONNECT-LIFECYCLE`: browser gateway session token, app foreground/idle/lock/disconnect transitions and background reconnection need one lease-aware lifecycle.
- `GAP-W09-OS-ENFORCED-EGRESS-CONTROL-AND-BYPASS-INVENTORY`: in-memory host allowlist is not an OS/container packet boundary; all direct, native, proxy, DNS, IPv6 and background paths need enforcement and inventory.
- `GAP-W03-W08-OFFLINE-OUTBOX-DURABILITY-AND-RECONCILIATION`: encrypted process-local outbox requires durable local storage, signed remote receipts, exact commit binding and unknown-effect reconciliation before deletion/replay.
- `GAP-W11-DISTRIBUTED-NETWORK-LEASE-REVOCATION-AND-FAILURE-DOMAIN`: global workload egress requires signed lease distribution, bounded revocation latency, region/network segmentation and failover that does not expand scope.

## 13. Decision status

This document is a cross-stream architecture proposal grounded in the inspected source paths. It does not accept an ADR, implement a network firewall, toggle Android radios, change the browser, revoke live sessions or prove that deployed NORYX7 traffic is already default-deny.

W01–W12 remain **PARTIAL**. The seven gaps above require owner review, architecture decision acceptance, implementation mapping and later adversarial validation. No integration or test campaign is authorized by this document.
