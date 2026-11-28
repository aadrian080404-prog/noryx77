# NORYX7 — Cross-Plane Failure Containment, Degraded Modes and Recovery Contract

**Review date:** 2026-11-28  
**Source-tree HEAD inspected:** `a5600924a8e12deb6f33e6adec3a23e2f880aa14`  
**Scope:** W01–W12; failure domains, containment, degraded operation, recovery and restoration evidence.  
**Phase:** architecture-only. No runtime, test, workflow, dependency, configuration, deployment or frozen-baseline change.

## 1. Purpose

This specification defines how NORYX7 behaves when dependencies fail, become stale, lose trust, disagree, partition or recover. It complements the dependency/ownership and execution-plane audits: a dependency graph is incomplete until every edge states what happens when its provider is unavailable or untrusted.

The objective is not maximum availability at any cost. NORYX7 must preserve authority boundaries, data integrity, user sovereignty and recoverability even when that means refusing work. Availability may degrade; authorization must never silently widen.

This is a proposed architecture contract, not evidence that the current repository implements a complete distributed failure-management system.

## 2. Source-grounded starting point

The inspected source already contains useful primitives, but their scope is bounded:

| Source | Blob SHA | Existing behavior | Boundary not established |
|---|---|---|---|
| `core/recovery.py` | `226193d08b0b8c57f275125e25b7823886ea163d` | Explicit NORMAL → INCIDENT → LOCKDOWN → TRUSTED_ONLY → RECOVERY → VERIFIED → NORMAL transitions; monotonic local epoch; guarded operation under lock | Durable/distributed epoch, quorum, node fencing, signed transition authority or recovery across process restart |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Offline states, bounded encrypted outbox, payload digest, execution-bound AAD and local conflict checks | Queue/sequence persistence, durable inbox, signed remote commit receipt and crash-safe deletion |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` | Bounded provider attempts, exclusion after exception, policy denial terminal | Safe retry when a provider may have performed an external effect before throwing or timing out |
| `ecosystem/global_scale.py` | inspected at source-tree HEAD above | In-process region/cell registries, health/capacity selection and explicit no-routable-cell failure | Distributed health authority, capacity reservation, leases, fencing and partition-safe placement |
| `noryx7_runtime/lifecycle.py` | `71d1079f0cf1aa9cd70a097ad2a9e6365dce38b5` | Immutable local CREATED/RUNNING/terminal execution lifecycle | Durable EFFECT_UNKNOWN/reconciliation lifecycle or cross-runtime transition authority |
| `noryx7_runtime/recovery.py` | `ecd5743a494a150e13556e5c3932b77a6b08aaa7` | Validates journal ordering, identities, duplicate steps, attestation chain and runtime binding | Recovery orchestration across independent journals, external effects and global membership |
| `core/agent_fabric.py` | `3704dd7bf66815274cc319c9583c45ae575f3d36` | Agent identity trust, skill registration and principal authorization callback at dispatch | Durable membership, lease expiry, distributed revocation propagation and independent fault-domain proof |
| `core/device_fabric.py` | `3b0ead031e03040d25bb7df3a716aaa50fa8591c` | Process-local device registry and online metadata | Hardware reachability proof, attestation, distributed presence lease or stale-device fencing |
| `core/egress.py` | `e50095f8a0265adfcac4812aa06778cece58fe83` | In-process default-deny component/host/port/protocol allowlist | OS-level mediation of all sockets, DNS rebinding/redirect control, lease expiry or global revocation |
| `core/observability.py` | `05dea0228b9b05c8684db7fe0aa890d7faa44485` | Bounded in-memory append-only event buffer; explicit capacity exhaustion | Durable external audit, event delivery guarantee or independent incident response |
| `core/alerting.py` | `f8caee629f5c7e1ec0446c0a7d9c18f7cf3ac1b8` | Verified-event gating and explicit escalation policy; delivery adapters external | Notification delivery proof, acknowledgement, retry/dead-letter or responder availability |
| `core/self_improvement.py` | `2cc85de48becd7243e6d3d572dded25841587a08` | Proposal-only staged improvement with external admission boundary | Durable signed release authorization, canary health, rollback and cross-node release fencing |

These primitives are not interchangeable. In particular, a local epoch is not a distributed fencing token; an online boolean is not reachability proof; a provider exception is not proof of no effect; and an alert record is not proof that a human received it.

## 3. Failure taxonomy and mandatory classification

Every dependency failure must be classified before retry, failover or state transition:

1. **UNAVAILABLE:** timeout, connection refusal, process loss or capacity exhaustion; effect may be absent or unknown.
2. **DEGRADED:** service responds but violates latency, freshness, accuracy, integrity or resource SLO.
3. **STALE:** artifact, policy, identity, device, model, route, evidence or membership version is older than its allowed validity.
4. **UNTRUSTED:** signature, attestation, identity, provenance, isolation or integrity check fails.
5. **CONFLICTED:** two valid-looking authorities or replicas report incompatible state.
6. **PARTITIONED:** network split prevents authoritative coordination or revocation confirmation.
7. **COMPROMISED:** credible evidence of unauthorized access, privilege misuse, tampering or boundary escape.
8. **UNKNOWN_OUTCOME:** request may have crossed the external effect boundary, but no authoritative receipt is available.
9. **RESOURCE_EXHAUSTED:** bounded queue, storage, CPU, memory, GPU, bandwidth, cryptographic quota or event capacity is exhausted.
10. **RECOVERING:** component is restarted but has not re-established identity, freshness, state continuity and policy eligibility.

A component must not collapse these into a generic FAILED state. Unknown outcome is especially important: it is neither success nor safe-to-retry failure.

## 4. Global operating modes

The system-wide mode is a policy-derived envelope, not a single health boolean. Components may report local modes, but the effective permission set is the intersection of global mode, local trust, policy, capability, data classification and resource lease.

| Mode | Allowed | Denied by default |
|---|---|---|
| NORMAL | Ordinary authorized work with full evidence and audit | Unmanifested capabilities |
| DEGRADED | Read-only, cached, local-only or reduced-risk work explicitly listed by policy | New high-impact external effects; hidden cloud fallback |
| DISCONNECTED | Local operations within unexpired offline snapshot and offline capability scope | Remote calls, unapproved sync, stale/revoked capabilities |
| QUARANTINED | Diagnostics, evidence preservation, safe export under explicit approval | Workload participation, credential reuse, state promotion |
| INCIDENT | Containment, evidence capture, incident coordination, explicitly safe continuity actions | Ordinary privileged actions and automatic failover from suspect component |
| LOCKDOWN | Minimal trusted control, revocation, isolation, recovery preparation | New user-facing side effects and untrusted execution |
| RECOVERY | Integrity checks, journal replay, identity re-enrollment, restore validation and controlled reconciliation | General workload execution |
| VERIFIED_RESUME | Canary/limited workload under fresh policy and trust evidence | Full traffic until release criteria are met |

Mode transitions require authenticated authority, reason code, evidence references, policy epoch and audit receipt. A service's own health endpoint cannot promote the global mode.

## 5. Dependency-edge contract

Every dependency edge in the system DAG must declare:

- provider and consumer component IDs;
- contract/schema version and compatibility range;
- required assurance level and freshness window;
- whether dependency is hard, soft, optional or conditional;
- timeout, retry budget, circuit-breaker threshold and backoff;
- idempotency/effect semantics and unknown-outcome behavior;
- fallback target and proof that it is an independent failure domain;
- permitted degraded capabilities and prohibited effects;
- data residency/classification constraints;
- cancellation and deadline propagation;
- revocation and epoch propagation;
- health signal source, trust and anti-spoofing;
- recovery handshake and evidence needed to restore traffic.

No fallback may inherit trust merely because it is available. If a hard dependency is unavailable, the consumer either enters an explicitly specified reduced mode or fails closed. Optional dependencies may be omitted only if the task contract declares the missing capability nonessential.

## 6. W01–W12 failure and containment matrix

| Stream | Representative failure | Immediate containment | Permitted degraded behavior | Resume evidence |
|---|---|---|---|---|
| W01 Identity/trust | issuer unavailable, key revoked, identity mismatch, stale session | deny new privileged grants; revoke/expire affected leases; quarantine unverifiable principals | public/non-sensitive local read-only tasks where policy permits | fresh issuer trust, key status, audience/session/device binding and revocation epoch |
| W02 Runtime/orchestration | coordinator crash, duplicate dispatch, lifecycle divergence | fence coordinator epoch; stop new dispatch; preserve attempt IDs | local planning or read-only inspection without execution authority | recovered canonical operation state, no duplicate attempt, current fencing token |
| W03 Memory/state/recovery | journal corruption, storage loss, split-brain commit, stale snapshot | freeze writes to affected namespace; preserve forensic copy; reject stale epoch | read-only verified snapshot within freshness limits | chain/checkpoint verification, namespace ownership, restore rehearsal and conflict resolution receipt |
| W04 Agent Fabric | agent compromised, registry unavailable, supervisor lost, identity revoked | isolate agent and revoke delegation; cancel/fence its active assignments | qualified independent agents only if assignment policy allows; otherwise queue or suspend | fresh agent attestation, skill qualification, delegation and supervisor quorum |
| W05 Routing/providers/resources | provider timeout after possible effect, router stale, node capacity loss | mark EFFECT_UNKNOWN; stop blind retry; revoke stale route/lease | safe alternate provider only after idempotency/reconciliation; reduced model tier only if policy permits | target receipt or no-effect proof, current route attestation, capacity lease and budget |
| W06 NEXUS/FRL/evidence | schema mismatch, proof checker unavailable, source provenance broken | quarantine affected claim/proof; prevent memory promotion | analysis may continue with explicit INDETERMINATE label and preserved dissent | exact schema/checker/source version, proof verification and provenance chain |
| W07 MIRROR WORLD | model fidelity drift, simulator failure, Reality Bridge telemetry unavailable | invalidate dependent simulation conclusions; block real-world actuation | offline scenario exploration clearly marked uncalibrated | calibrated model version, holdout validation, source observations and separately authorized bridge |
| W08 Surfaces/devices/offline | device lost, browser egress path bypass, stale offline snapshot | expire device/session leases; deny network by default; retain encrypted pending outbox | local offline tasks under snapshot scope; no unsupported remote action | device re-enrollment/attestation, fresh policy snapshot, signed sync/commit receipts and egress verification |
| W09 Security/crypto/audit/release | key compromise, event buffer full, verifier unavailable, integrity alert | fail closed for affected trust domain; preserve evidence; freeze release/rotation-sensitive actions | isolated diagnostic mode with separate audit path | key rotation/revocation proof, independent verifier, durable external audit checkpoint and release attestation |
| W10 Domain/specialists | specialist unqualified, jurisdiction mismatch, data source stale | block domain conclusion or high-impact recommendation | general explanation with uncertainty; refer to qualified human | credential/scope verification, jurisdiction, fresh source evidence and independent domain review |
| W11 Global operations | region partition, stale capacity, node replacement, control-plane loss | fence old epoch/node; prevent split-brain ownership; stop unsafe placement | local autonomous cell only within pre-authorized lease and data residency scope | quorum/authority recovery, new fencing epoch, membership attestation, capacity reservation and replay reconciliation |
| W12 Economy/governance/impact | payment outcome unknown, ledger conflict, quorum invalid, impact evidence disputed | freeze affected settlement/vote/claim; do not double-pay or erase record | read-only statements and pending status | provider settlement receipt, double-entry reconciliation, governance appeal/quorum proof or independent impact audit |

## 7. Recovery state machine

Each component and operation has a local lifecycle; the global recovery protocol coordinates them without pretending they share one in-memory controller.

**Required sequence:**

1. DETECT — capture signed/traceable failure evidence and classify failure type.
2. CONTAIN — revoke affected capabilities, isolate suspect nodes, stop unsafe dispatch and preserve volatile evidence where feasible.
3. FENCE — advance authoritative epoch and reject all stale leases, sessions, workers, queued dispatches and replicas.
4. SNAPSHOT — preserve journals, queue metadata, key versions, deployment digest and evidence before repair.
5. RECONSTRUCT — restore from an authenticated checkpoint; replay only records whose identity, sequence, signature, schema and namespace validate.
6. RECONCILE — resolve external effect outcomes, offline operations, duplicate delivery, conflicting replicas and cross-store partial commits.
7. VERIFY — independent checks of identity, policy, keys, software, state chain, data integrity, evidence freshness, egress and monitoring.
8. CANARY — admit limited non-critical traffic with explicit budget and automatic stop thresholds.
9. RESUME — advance to VERIFIED_RESUME then NORMAL only after named authorities approve and receipts are committed.
10. REVIEW — record incident timeline, root cause, residual risk, corrective action and evidence retention/disposal decision.

No direct transition from INCIDENT, LOCKDOWN, QUARANTINED or RECOVERING to NORMAL is allowed. A component restart is not recovery completion.

## 8. Retry, failover and side-effect rules

### 8.1 Retry classes

- **Pure/idempotent computation:** retry within bounded deadline and budget if input digest and policy epoch remain valid.
- **Read-only external request:** retry only when source freshness and privacy/egress rules remain valid.
- **Idempotent write:** retry only with the same stable operation ID/idempotency key and target-side deduplication semantics.
- **Non-idempotent write:** never blind retry after timeout/connection loss; enter UNKNOWN_OUTCOME and query/reconcile target state.
- **Security/financial/physical action:** require action-specific authorization, effect receipt and recovery policy; failover is a new dispatch decision, not a transparent transport retry.

### 8.2 Circuit breakers

Each provider/agent/node/domain adapter needs a breaker keyed by target identity and capability, not a single global counter. States: CLOSED, OPEN, HALF_OPEN, QUARANTINED. Breaker state is advisory for routing; it cannot replace trust revocation or policy denial. HALF_OPEN probes are bounded, non-mutating and independently authorized. QUARANTINED requires explicit re-admission.

### 8.3 Failover independence

A fallback is not independent if it shares the failed credential, signing key, control plane, network path, storage namespace, operator authority, model provider or deployment artifact that caused the failure. Failure-domain metadata must identify shared dependencies and correlated-risk groups. If independence cannot be demonstrated, treat failover as same-domain retry and apply the stricter rule.

## 9. Offline, partition and reconnect contract

- Offline execution is permitted only from a signed, unexpired, principal/device/audience-bound snapshot with a declared offline capability set.
- Offline authorization cannot extend expiry, widen scope, override revocation evidence already known locally, or authorize high-impact actions that require online confirmation.
- The outbox must be durable and append-only until a typed remote commit receipt is verified.
- A remote acceptance receipt means only that the server received the operation; it is not proof of effect or final commit.
- Reconnect uses authenticated peer identity, audience, channel binding, policy epoch and freshness; caller-supplied booleans are not sufficient.
- Duplicate/reordered messages are deduplicated by stable operation/attempt IDs and monotonic namespace sequence.
- Conflicts become explicit reconciliation records; last-write-wins is forbidden for authority, money, identity, security policy and irreversible effects.
- A network partition never creates a second global authority. Local cells may continue only inside pre-delegated leases and bounded scope.

## 10. Monitoring, alerting and human escalation

Every critical state transition must create a durable event with event ID, source component identity, monotonic sequence, time source quality, policy epoch, evidence digest, correlation/operation IDs and integrity protection.

Alert delivery is a separate lifecycle: CREATED → QUEUED → SENT → ACKNOWLEDGED or DELIVERY_UNKNOWN/FAILED. A local AlertRouter record does not mean notification delivery. Emergency calling or other external escalation requires explicit user/org policy, jurisdiction and provider confirmation; no silent automatic emergency action.

Loss of the primary observability path must not silently disable containment. Critical security and financial paths need an independent bounded emergency audit channel and a defined behavior when both primary and secondary channels are unavailable. Buffer exhaustion must cause a deliberate mode transition, not silent event loss.

## 11. Recovery and degraded-mode invariants

1. Fail closed for authority; degrade availability only where explicitly safe.
2. No fallback may broaden capability, identity scope, data residency or retention.
3. No retry after ambiguous side effect without idempotency or target reconciliation.
4. No state promotion from stale, untrusted or conflicted evidence.
5. No restart may restore expired credentials or stale leases.
6. No local online flag substitutes for attested reachability.
7. No simulation or model output authorizes a real-world action.
8. No alert record substitutes for delivery acknowledgement.
9. No health/readiness signal is trusted without identity and freshness.
10. No component can self-certify its own recovery where it was the source of the incident.
11. All modes preserve user control, revocation and data minimization.
12. All decisions preserve provenance and distinguish UNKNOWN, INDETERMINATE, FAILED and VERIFIED.

## 12. Required integration/verification campaign (deferred)

When the architecture phase is formally closed, tests must include:
- kill/restart of every critical dependency between reservation, dispatch, effect, verification and commit;
- partitions on both sides of quorum, stale leader and old-node rejoin;
- expired/revoked identity while work is queued or in flight;
- timeout after target accepted a write but before receipt returns;
- duplicate/reordered offline sync, crash before/after durable acknowledgement;
- provider failover with shared credential/control-plane and deliberately correlated failure;
- memory/journal restore from stale, truncated, forked and schema-incompatible checkpoints;
- observability buffer exhaustion, alert delivery unknown and loss of both audit paths;
- device/network lease expiry while sockets, WebView subresources, downloads and background jobs are active;
- domain evidence expiration, checker outage and simulator fidelity drift;
- ledger settlement unknown, duplicate payout, split-brain governance quorum and disputed impact measurement;
- canary rollback, release-key compromise and stale deployment rejoin.

Tests must assert both safety and liveness: denied actions stay denied, and recovery can complete after valid evidence is restored. Tests are not run in this architecture-only phase.

## 13. New cross-stream gaps

- `GAP-W01-W09-TRUST-DEPENDENCY-LOSS-AND-REVOCATION-PROPAGATION`: issuer, key or revocation-service outage must not create fallback identity or stale privilege.
- `GAP-W02-W03-DURABLE-GLOBAL-RECOVERY-EPOCH-AND-FENCING`: current local recovery epoch needs distributed durable authority and stale worker/node fencing.
- `GAP-W02-W05-UNKNOWN-EFFECT-AND-SAFE-FAILOVER`: provider exceptions/timeouts may follow external effects; shared idempotency and reconciliation are required before retry.
- `GAP-W03-W08-DURABLE-OFFLINE-OUTBOX-INBOX-AND-COMMIT-ACK`: in-memory queue/sequence and local acknowledgement do not establish crash-safe remote commit.
- `GAP-W04-W11-DISTRIBUTED-AGENT-AND-NODE-MEMBERSHIP-LEASES`: agent/device online metadata needs attested leases, expiry, revocation propagation and rejoin fencing.
- `GAP-W06-W07-EVIDENCE-AND-SIMULATION-DEGRADATION-INVALIDATION`: stale sources, unavailable proof checkers or fidelity drift must invalidate dependent claims and block Reality Bridge actuation.
- `GAP-W09-W11-DURABLE-INDEPENDENT-AUDIT-AND-ALERT-DELIVERY`: in-memory event/alert queues need durable independent audit, delivery acknowledgement and explicit buffer-exhaustion behavior.
- `GAP-W10-DOMAIN-SPECIALIST-AND-EVIDENCE-STALE-MODE`: specialist unavailability or expired jurisdiction/source evidence must produce INDETERMINATE, not fabricated certainty.
- `GAP-W11-GLOBAL-PARTITION-QUORUM-AND-REJOIN-FENCING`: regional partitions and stale nodes require consensus authority, fencing epochs and safe rejoin.
- `GAP-W12-FINANCIAL-GOVERNANCE-UNKNOWN-OUTCOME-RECOVERY`: uncertain settlement, ledger conflict and governance quorum failure need frozen/pending states and independent reconciliation.

## 14. Decision status

This document adds failure semantics to all W01–W12 without changing the existing canonical plane enum or creating a second authority model. It is an architecture proposal, not accepted ADR, implementation or verification. Source observations are bounded to the files and revision listed above; external infrastructure controls are not ruled out. No tests were run. **W01–W12 remain PARTIAL.**
