# NORYX7 — Global Temporal Consistency, Clock Trust, Causal Ordering and Freshness Contract

**Status:** architecture proposal; all decisions OPEN; W01–W12 remain PARTIAL  
**Source snapshot reviewed:** `daf9f5b28f923934729af28911fb01a5f33f05e5`  
**Scope:** cross-plane temporal semantics for identity, authorization, execution, memory, evidence, devices, offline operation, distributed placement, simulation and financial governance.  
**Change boundary:** architecture documentation only. No runtime, test, workflow, dependency, deployment or frozen-baseline changes.

## 1. Executive rule

NORYX7 must never treat a timestamp supplied by a node, provider, model, browser, device or external data source as sufficient proof of event order, freshness, authorization validity or commit precedence.

The system distinguishes five independent questions:

1. **When does a source claim an event happened?** — wall-clock assertion, with provenance and uncertainty.
2. **How long has this process or device observed elapsed time?** — local monotonic duration, valid only within its clock domain and boot/session lifetime.
3. **Which event causally depends on which other event?** — explicit parent/correlation links and logical ordering metadata.
4. **Which writer/authority generation is allowed to commit?** — durable fencing epoch or lease generation, checked at the resource that accepts the write.
5. **How fresh and trustworthy is the evidence now?** — policy-bounded age, issuer/source status, revocation freshness and validity scope.

No one of these values substitutes for another. UTC timestamps do not create causality; a Lamport/HLC value does not prove real elapsed time; a local monotonic counter is not portable across reboots; a sequence number is not global unless its namespace and authority are explicit; a lease expiry is not fencing unless stale writers are rejected by the protected resource.

## 2. Bounded source reconciliation

The following observations are anchored to the source snapshot above. They describe the inspected implementation, not every possible deployment or external infrastructure control.

| Source | Observed implementation | Temporal boundary not established |
|---|---|---|
| `core/identity.py` | Ed25519 agent identity and attestation primitives; `IdentityRegistry` stores approved keys in a process-local dictionary and revocation removes a key under a local lock | Durable, distributed revocation epoch; issuer validity interval; trusted timestamp; cross-node propagation/freshness contract |
| `core/actions.py` | HMAC grants include `expires_at`; authority defaults to `time.monotonic` and tracks consumed nonces locally | A monotonic value is meaningful only in its originating clock domain; it cannot be serialized as a portable absolute expiry or compared across nodes/reboots |
| `core/offline.py` | Offline snapshot uses integer `issued_at`, a supplied clock, local highest-issued timestamp/ID and optional monotonic anchor; queue sequence is process-local | Signed not-before/not-after/issuer time-quality contract, rollback-resistant durable high-water mark, clock uncertainty policy and durable global namespace |
| `core/recovery.py` | Local controller increments an in-process epoch on state transitions and guards a critical section | Epoch durability, cross-process authority, region-wide fencing and stale-writer rejection at remote storage/provider |
| `core/state_journal.py` | SQLite WAL/FULL, per-journal sequence, schema version and SHA-256 digest; recovery checks contiguous sequence beginning at 1 | Global ordering across journal files/nodes, trusted time, signed checkpoint, journal namespace/owner and cross-journal causal merge |
| `noryx7_runtime/state.py` | Separate in-memory runtime journal with local append order, reservations and attestation chain | Shared temporal namespace or merge contract with Core SQLite journal |
| `core/finch.py` | Observations accept numeric floating-point timestamps; event graph records relationships; forecast averages severity | Clock source, timestamp uncertainty, out-of-order ingestion policy, event-time vs processing-time distinction, late-event correction and calibrated temporal forecast |
| `ecosystem/global_scale.py` | Local region/cell/capacity and queue primitives; queue has a local sequence; time-related metric values carry timestamps | Distributed lease expiry, quorum-issued epoch, clock-quality admission and globally fenced capacity reservation |

The source contains useful local primitives. This audit does not claim that external NTP/PTP services, database clocks, cloud leases or deployment controls do not exist; their composition with these contracts is not demonstrated in the inspected paths.

## 3. Canonical temporal model

Every time-bearing record MUST identify its time domain. The common envelope should support:

- `event_time_utc`: source-asserted UTC instant, if available.
- `observed_at_utc`: time at which the receiving observer recorded the event.
- `received_at_utc`: ingestion boundary time, distinct from event time.
- `clock_domain_id`: issuer/device/process/boot identity defining the clock domain.
- `clock_source`: authenticated or declared source and its assurance class.
- `uncertainty_bound_ms`: bounded estimate of timestamp error; unknown is represented explicitly, never as zero.
- `monotonic_elapsed`: optional duration measurement plus clock-domain and boot/session binding; never exported as a cross-node absolute time.
- `logical_time`: Lamport or Hybrid Logical Clock tuple, including algorithm/version and node identity.
- `causal_parents`: explicit predecessor/event IDs or a bounded causal context.
- `namespace_sequence`: strictly increasing sequence inside a named journal/stream/partition, with owner and epoch.
- `authority_epoch`: fencing generation issued by the relevant authority.
- `validity_interval`: issuer-defined not-before/not-after interval and permitted skew policy.
- `freshness_policy_id`: policy determining maximum age, source requirements and stale-data action.

All optional fields must have typed absence semantics. An unknown timestamp is not epoch zero. A missing causal parent is not proof that no dependency exists. A logical timestamp is not a trusted wall-clock timestamp.

## 4. Time domains and permitted use

### 4.1 Wall-clock UTC

Use UTC instants for human-readable audit, external event claims, expiry windows and cross-system reporting only when source identity, synchronization assurance and uncertainty are recorded.

Wall-clock time may jump forward or backward due to synchronization, administrator changes, VM restore, battery loss or compromise. Therefore:

- never use a wall clock alone for local timeout measurement;
- never infer causality from timestamp ordering alone;
- detect and record discontinuities;
- reject or quarantine expiry decisions when uncertainty overlaps the validity boundary unless a policy explicitly permits a conservative bounded-skew rule;
- preserve original source time and receiver observation time separately.

### 4.2 Monotonic time

Use monotonic clocks for elapsed durations, local deadlines, timeout budgets and rate limiting within the same process/device boot clock domain.

A monotonic reading MUST carry a clock-domain identifier and boot/session generation. It MUST NOT be copied into a portable authorization token as though it were a globally comparable expiry. After reboot, restore or clock-domain change, prior monotonic deadlines are invalid and must be reconstructed from trusted issuer metadata or treated as unknown.

### 4.3 Logical and causal time

Use Lamport ordering or a Hybrid Logical Clock (HLC) only as an ordering aid. HLC combines a physical-time component with a logical counter, but it does not establish that physical clocks are correct. Every HLC value is bound to node identity and algorithm version.

For causal dependencies, retain explicit parent IDs or a version vector/causal context where the concurrency semantics require it. If two events are concurrent, do not manufacture a total causal order merely to make a merge deterministic.

### 4.4 Sequence and epoch

A sequence is monotonic only within its declared namespace. A journal sequence of 42 on node A is not necessarily later than sequence 41 on node B.

A fencing epoch is different: it is an authority generation. A resource accepting writes MUST validate the current epoch/generation at commit time, so a stale node cannot commit merely because it still believes its lease is valid.

## 5. Clock trust and quality lifecycle

Define a `ClockQualityStatement` with:

- clock domain, node/device identity and boot generation;
- source class (hardware RTC, authenticated time service, platform service, operator-set, inferred, unknown);
- last synchronization observation and synchronization method;
- measured/declared offset and uncertainty bound;
- drift estimate and maximum permitted holdover;
- monotonic continuity status;
- leap-second/smear handling profile;
- rollback/jump detection state;
- attester identity, signature and policy version.

Clock quality states are proposed as `TRUSTED`, `BOUNDED`, `HOLDOVER`, `UNTRUSTED`, `ROLLBACK_SUSPECTED`, `UNAVAILABLE`. They are descriptive evidence, not privilege levels.

Policy behavior:
- `TRUSTED`: time-dependent actions may proceed within the declared uncertainty and validity limits.
- `BOUNDED` / `HOLDOVER`: allow only operations whose safety margin exceeds the uncertainty and whose policy explicitly permits holdover.
- `UNTRUSTED`: do not make expiry, freshness or ordering decisions that require trustworthy time; use causal/fencing state if sufficient, otherwise suspend.
- `ROLLBACK_SUSPECTED`: freeze authority-sensitive writes, preserve forensic evidence and require trusted resynchronization/reconciliation.
- `UNAVAILABLE`: no automatic privilege extension; only pre-authorized offline capabilities with independently valid bounded freshness evidence may continue.

No node may improve its own clock-quality classification merely by reporting successful synchronization. The time source and measurement evidence must be independently authenticated or explicitly classified as lower assurance.

## 6. Authorization, sessions, capabilities and leases

A signed authorization should carry issuer time, validity interval, subject/principal, device/workload, audience, scope, policy epoch, revocation handle, nonce, key ID and canonical signature preimage.

Validation rules:
1. Verify signature, issuer trust, audience, scope and revocation state before evaluating time.
2. Apply one explicit maximum-skew policy; do not silently widen it per caller.
3. If the uncertainty interval crosses not-before/not-after, return `INDETERMINATE_TIME` unless a narrower conservative rule resolves it.
4. For local elapsed TTL, derive a monotonic deadline at admission and bind it to the local clock domain/boot generation.
5. For distributed leases, require both expiry and a monotonically increasing fencing token from the lease authority.
6. The target storage/provider/device must reject a stale fencing token at the point of effect; checking only at the coordinator is insufficient.
7. Revocation freshness is independent of token expiry. An unexpired token with stale/unknown revocation state is not automatically valid for high-impact actions.
8. Clock rollback, reboot or uncertainty growth must never extend a capability.

## 7. Operation lifecycle and causal commit

Every cross-plane operation carries stable `operation_id`, per-dispatch `attempt_id`, idempotency key, principal/device/audience, policy epoch, authority epoch, causal parents and namespace sequence.

Required event lifecycle:

`INTENT_RECORDED → AUTHORIZED → RESERVED → DISPATCHED → EFFECT_OBSERVED | EFFECT_UNKNOWN → VERIFIED → COMMIT_PREPARED → COMMITTED`

Failure branches include `REJECTED`, `CANCELLED`, `EXPIRED`, `CONFLICT`, `RECONCILIATION_REQUIRED`. A timeout after dispatch is `EFFECT_UNKNOWN`, not `FAILED_NO_EFFECT`.

Each transition records:
- event ID and transition ID;
- previous-state digest and expected version;
- operation/attempt/idempotency IDs;
- causal parent(s);
- namespace sequence and fencing epoch;
- source and receiver time with uncertainty;
- authorization and verification receipt IDs;
- effect/commit receipt, if one exists.

Commit preconditions must be checked atomically at the authoritative state owner: expected version, current fencing epoch, authorization freshness, revocation policy, causal preconditions and effect receipt. A local wall-clock timestamp cannot resolve a concurrent write conflict.

## 8. Memory, journals and replication

Memory and journal records must distinguish event time, ingestion time, commit order and causal dependencies.

Required design:
- stable record ID and namespace/tenant/owner;
- per-partition sequence and authority epoch;
- source event time plus uncertainty and receiver ingestion time;
- causal parents and content/version digest;
- schema version and migration lineage;
- retention/expiry policy and tombstone semantics;
- signed checkpoint or independently anchored journal head;
- explicit conflict state for concurrent updates.

Merge rules:
- never use last-write-wins based solely on wall-clock timestamps for identity, authorization, security policy, money, irreversible actions or evidence status;
- use compare-and-swap against an expected version for single-object updates;
- use causal merge only for data types whose semantics are explicitly mergeable;
- preserve concurrent versions and surface conflicts where automatic merge is not proven safe;
- tombstones must dominate only within an authenticated namespace/epoch and retention policy; stale replicas cannot resurrect deleted or revoked state;
- checkpoint age is evaluated with clock quality and external anchor evidence, not local timestamp alone.

A journal sequence is scoped to `journal_id + owner_id + epoch`. Cross-journal reconciliation creates a new signed merge/commit record; it must not rewrite history to create a fictional global sequence.

## 9. Offline and disconnected operation

Offline snapshots must include issuer-signed `issued_at`, `not_before`, `not_after`, policy epoch, artifact version, principal/device/audience, capabilities, source clock-quality evidence, snapshot sequence and revocation watermark.

Admission must verify:
- signature and trusted issuer;
- snapshot namespace and rollback-resistant anchor;
- local clock-quality bounds and conservative age policy;
- device/boot identity and permitted offline duration;
- policy and artifact compatibility;
- revocation watermark freshness and any known local revocation;
- capability allowlist and prohibited high-impact actions.

If time quality becomes untrusted while disconnected, NORYX7 must not extend offline authority. It may continue only tasks whose safety does not depend on uncertain expiry and whose offline lease was validly admitted with a conservative bounded duration. Otherwise it suspends and preserves queued work.

The outbox sequence is local to a durable namespace and boot-independent store. Reconnect uses stable operation IDs and idempotency. A signed remote commit receipt binds exact operation, attempt, payload digest, effect, final state version, remote namespace sequence, fencing epoch and server clock-quality statement. Only after verifying this receipt may a tombstone be committed atomically. Acceptance/receipt time is not a substitute for final commit.

## 10. Evidence, NEXUS/FRL, FINCH and MIRROR WORLD

Evidence records need two timelines:
- **event timeline:** when the source says the observation occurred;
- **knowledge timeline:** when NORYX7 received, checked, transformed and admitted it.

Each evidence item records source clock quality, original timestamp, uncertainty, receiver timestamp, ingestion sequence, provenance, validity interval, freshness policy and supersession/correction links.

NEXUS/FRL must not infer that a claim preceded another claim merely because timestamps sort that way. Causal proof uses explicit dependency edges and source spans. A stale verifier, revoked signer, changed source, clock rollback or expired validity scope invalidates dependent claims or moves them to `INDETERMINATE`; it does not silently rewrite history.

FINCH must separate event-time processing from arrival-time processing, handle late/out-of-order observations, retain corrections and expose clock-quality limitations. Its current mean-severity forecast is not a calibrated temporal probability and must not be presented as one.

MIRROR WORLD simulation time is a separate virtual clock domain. Time acceleration, pause, branching and replay must never be confused with real-world event time. Every bridge between simulated and observed reality records explicit mapping, scale, model version, calibration interval and uncertainty. A simulation timestamp cannot authorize a physical action or be admitted as empirical event evidence.

## 11. Global topology, consensus and region partitions

Global membership, leases, capacity reservations and leader changes require:
- authority-issued monotonically increasing epoch;
- quorum or other explicitly selected consensus/fencing authority;
- node identity and attestation bound to membership generation;
- per-region/partition sequence namespace;
- lease expiry with bounded clock assumptions;
- resource-side fencing on every mutation;
- explicit partition policy: continue only within pre-delegated capabilities and lease bounds; never create a second global writer;
- safe rejoin requiring state reconciliation, stale-epoch rejection and new lease issuance.

A node's local `online` flag, heartbeat timestamp or self-reported time is not proof of reachability, leadership or current authority. Heartbeats are failure-detector inputs with uncertainty, not security credentials.

## 12. Financial, governance and impact time

Financial operations distinguish authorization time, provider acceptance time, external effect time, settlement time, ledger commit time and reconciliation time. Provider timestamps are evidence claims and must be authenticated; they do not replace provider transaction IDs, idempotency keys or signed settlement receipts.

Ledger ordering is based on the ledger's authoritative sequence and transaction invariants, not client clocks. Corrections are append-only reversals/adjustments, not timestamp rewrites. A payout, contribution, vote or treasury reservation whose external result is uncertain remains pending/frozen until independent reconciliation. Governance windows and quorum membership use issuer-authorized epochs and eligibility snapshots; wall-clock cutoffs require explicit trusted-time and skew rules. Impact measurements preserve measurement period, ingestion period, baseline version, counterfactual version and correction lineage.

## 13. Temporal contracts to standardize

Proposed typed records (names are provisional):
- `ClockQualityStatement`
- `TimeObservation`
- `TemporalValidityWindow`
- `CausalEventEnvelope`
- `CausalContext`
- `NamespaceSequence`
- `AuthorityEpoch`
- `FencedLease`
- `RevocationWatermark`
- `TemporalFreshnessDecision`
- `TemporalConflictRecord`
- `TemporalMergeReceipt`
- `SignedCheckpointReceipt`
- `OfflineTemporalAdmissionReceipt`
- `TemporalCommitReceipt`
- `SimulationClockMapping`

All records require versioned schemas, canonical wire encoding, signature domain separation and explicit unknown/absent semantics. They must reuse the cross-plane canonical envelope rather than introduce a second incompatible identity or signature system.

## 14. Decisions still OPEN

1. Select the authoritative time-source trust model for client, edge, regional and critical nodes; evaluate authenticated NTP, NTS, PTP and hardware/platform sources against deployment classes.
2. Select HLC vs Lamport plus explicit causal vectors per workload; do not force one global clock algorithm onto every data type.
3. Define maximum offset, uncertainty, drift, holdover and skew thresholds per risk class and jurisdiction.
4. Select the distributed fencing/epoch authority and resource-side enforcement protocol.
5. Define durable namespace sequence, signed checkpoint and cross-journal merge semantics.
6. Define revocation watermark distribution, freshness windows and disconnected behavior.
7. Define leap-second/smear profile and time-source failover policy.
8. Define retention, privacy and residency of temporal telemetry and clock-quality attestations.
9. Define simulation-to-reality clock mapping and prohibit accidental promotion of virtual timestamps.
10. Define financial provider timestamp authentication, settlement ordering and ledger time policy.

These are design decisions, not implementation assumptions. No time synchronization technology, consensus protocol or clock provider is declared selected by this document.

## 15. Workstream impact W01–W12

| Stream | Temporal closure requirement |
|---|---|
| W01 Identity/trust | Issuer validity, session expiry, revocation watermark, device/boot binding and bounded clock uncertainty |
| W02 Runtime/orchestration | Causal operation lifecycle, transition order, deadlines and unknown-outcome reconciliation |
| W03 Memory/state/recovery | Namespace sequences, durable epochs, signed checkpoints, MVCC/causal merge and rollback detection |
| W04 Agent fabric | Agent lease/heartbeat separation, attestation freshness, assignment epoch and result causal lineage |
| W05 Routing/providers | Provider attempt/effect/settlement timelines, idempotency and authenticated receipts |
| W06 NEXUS/FRL/evidence | Event-time vs knowledge-time, evidence freshness, causal proof dependencies and correction lineage |
| W07 MIRROR WORLD | Isolated virtual clock, replay/branch determinism and explicit reality-time mapping |
| W08 Surfaces/devices/browser/offline | Boot-bound monotonic deadlines, trusted offline snapshot validity, reconnect and lease expiry |
| W09 Security/crypto/audit/release | Trusted time evidence, key/revocation validity, signed checkpoints and rollback-resistant audit |
| W10 Specialist/domain intelligence | Credential/jurisdiction validity windows, source freshness and temporal calibration |
| W11 Global distribution/operations | Distributed epochs, fencing, partition-safe membership, quorum and safe rejoin |
| W12 Economy/governance/impact | Authoritative ledger sequence, settlement proof, voting windows, measurement periods and correction history |

## 16. New bounded closure gaps

- `GAP-W01-W08-CLOCK-QUALITY-AND-TRUSTED-EXPIRY`: authenticated time-source assurance, uncertainty, drift, holdover and conservative expiry semantics.
- `GAP-W02-W03-W06-CAUSAL-EVENT-ORDER-AND-LATE-ARRIVAL`: causal context, event-time/ingestion-time separation, out-of-order handling and correction lineage.
- `GAP-W02-W03-W11-DURABLE-NAMESPACE-SEQUENCE-AND-FENCING-EPOCH`: durable scoped sequence and authority epoch enforced by the commit target.
- `GAP-W01-W09-REVOCATION-WATERMARK-AND-TEMPORAL-VALIDITY`: issuer/device/session revocation freshness independent from token expiry.
- `GAP-W03-W06-W09-SIGNED-CHECKPOINT-TIME-AND-ROLLBACK-DETECTION`: signed external checkpoint, trusted timestamp evidence and rollback-resistant recovery.
- `GAP-W04-W05-W11-LEASE-EXPIRY-AND-STALE-WRITER-REJECTION`: node/agent/provider lease with resource-side fencing and safe rejoin.
- `GAP-W06-W07-VIRTUAL-CLOCK-AND-REALITY-TIME-SEPARATION`: simulation clock domain, replay mapping and no promotion to empirical/actuation authority.
- `GAP-W10-W12-DOMAIN-AND-FINANCIAL-TEMPORAL-FRESHNESS`: jurisdiction/source expiry, settlement time proof, ledger ordering and temporal impact correction.

These gaps overlap prior clock, offline, fencing and evidence gaps but identify the common temporal contract needed to close them. They are not claims of confirmed vulnerabilities.

## 17. Deferred integration and verification campaign

After architecture review and formal closure only:
- inject clock jumps forward/backward, skew, drift, holdover and loss of time source;
- reboot/restore nodes and verify monotonic clock-domain invalidation;
- replay expired, future-dated, revoked and same-time-conflicting tokens/snapshots;
- deliver events out of order, duplicate, late and with conflicting causal parents;
- create concurrent writes on partitioned replicas and verify conflict preservation;
- attempt commits from stale epochs after leader/lease transfer;
- test stale node rejoin and fencing at the actual storage/provider boundary;
- crash around journal checkpoint, offline outbox, receipt and tombstone commits;
- verify signed remote receipts bind exact operation/effect/final version;
- invalidate evidence when source, signer, checker, credential or jurisdiction expires;
- replay MIRROR WORLD scenarios under virtual time without altering real-world audit time;
- test payment settlement, ledger correction, voting cutoff and impact-period reconciliation with skewed clocks.

Tests must cover safety and liveness, and must not treat a successful clock sync as proof of distributed consistency. **No tests are run in this architecture-only pass.**

## 18. Status

This contract extends the existing architecture without changing the canonical 18-plane registry or creating a new authority model. All technology choices and thresholds remain OPEN. The source observations are bounded to the inspected snapshot. No runtime code, tests, workflows, dependencies or deployment files were changed. **W01–W12 remain PARTIAL; architecture closure, integration, comprehensive verification and operational readiness are not claimed.**
