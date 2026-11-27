# NORYX7 — Global Temporal Consistency, Causal Order and Version Authority Architecture

**Status:** architecture proposal / source reconciliation; not an accepted ADR and not implemented  
**Workstreams:** W01–W12  
**Reviewed branch snapshot:** `daf9f5b28f923934729af28911fb01a5f33f05e5` (PR #212 head at review start)  
**Scope:** identity, authorization, operations, memory, evidence, devices, offline execution, distributed placement, audit, specialists, finance and governance.

## 1. Purpose and governing invariant

NORYX7 must not treat a timestamp as proof that an event is newer, authorized, causally downstream or still valid. Devices may have skewed or rolled-back wall clocks; nodes may be disconnected; event delivery may be delayed or reordered; policy and revocation versions may advance while a replica is offline; and two regions may each believe they are current.

The system therefore needs a **temporal consistency contract** that separates:

1. physical time reported by a clock;
2. monotonic elapsed time measured inside one running process/device;
3. causal order between events;
4. authoritative version order for a named state/authority domain;
5. validity intervals for credentials, evidence, policy and leases;
6. ingestion/commit time at the authority that accepts an event.

The governing invariant is:

> No wall-clock timestamp, local sequence, cached policy, replica observation or delayed message may by itself grant authority, establish causal order, supersede an authoritative version, or prove that an external effect committed.

This is a design contract, not a claim that the current repository implements global time synchronization or consensus.

## 2. Source reconciliation (bounded)

The review inspected the following current source paths and recorded their blob identities:

| Source | Blob SHA | What it currently establishes | What it does not establish |
|---|---|---|---|
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite WAL/FULL, per-row digest, unique sequence and contiguous replay from sequence 1 | Signed/global authority epoch, cross-region sequence ownership, trusted timestamp, cross-journal causal merge |
| `core/identity.py` | `e6e8e5b03135251baca489643f86c7d81a755a08` | Ed25519 agent identity/attestation and a lock-protected in-process trust registry | Durable distributed revocation version, issuer time authority, stale-replica fencing or credential validity history |
| `core/device.py` | `4f7d82ec5a1e40b595c4c341ab7d3ed551f3ac14` | Capability grant has integer `expires_at` and `epoch`; gate compares caller-supplied `now` and `epoch` | Trusted time source, rollback-resistant clock, epoch authority, signed grant lifecycle or remote revocation propagation |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | Offline snapshot has `issued_at`, policy/artifact/state versions and integrity digest; a monotonic-anchor protocol is injectable | By field presence alone, signed issuer time, globally comparable version, causal history or a durable distributed authority |
| `ecosystem/global_scale.py` | inspected at reviewed branch snapshot | Region/cell health, capacity and version labels; local selection under locks | Distributed leases, monotonic fencing tokens, quorum-backed ownership or causal replication |
| `core/observability.py` | `05dea0228b9b05c8684db7fe0aa890d7faa44485` | Event records carry `time.time()` and a local increasing event ID | Trusted timestamp, causal order across nodes, durable global event sequence or authenticated clock provenance |
| `core/finch.py` | `4de84c583ba41faa6ff169dd7ed28f2306ed1d09` | Observations carry a numeric timestamp; event graph records explicit relation edges | Clock-quality metadata, event-time vs ingest-time distinction, causal completeness or temporal calibration |
| `core/audit.py` | `61deb17b4e9afba8b2b5a582de79d8089d3b51b8` | In-process append-only hash chain and HMAC checkpoint against a configured key provider | Durable external timestamping, global order, independent checkpoint custody or distributed chain reconciliation |

These are bounded source observations. External NTP/PTP, operating-system protections, deployment control planes, KMS/HSM services or database guarantees may exist outside the inspected paths and are not ruled out.

## 3. Canonical temporal event envelope

Define a versioned, language-neutral `TemporalEventEnvelope` (proposal) for events crossing process, device, region or language boundaries:

- `event_id`: globally unique, immutable event identifier;
- `event_type` and `schema_version`;
- `tenant_id`, `authority_domain`, `aggregate_id` and `stream_id`;
- `issuer_id`, authenticated `principal_id`, `device_or_workload_id`, and audience;
- `operation_id`, `attempt_id`, optional `effect_id`, `causation_id`, `correlation_id`;
- `observed_at`: source-reported event time, plus clock source and quality;
- `issued_at`: issuer's asserted time;
- `accepted_at`: authority's receipt/acceptance time;
- `hlc`: hybrid logical clock tuple (physical component, logical counter, node identity);
- `causal_context`: bounded vector/version context or explicit parent event IDs;
- `aggregate_sequence` and `authority_epoch`;
- `base_version`, `result_version`, `policy_version`, `revocation_epoch`;
- `valid_from`, `valid_until` where the domain defines a validity interval;
- `payload_digest`, provenance references, classification and retention;
- `signature_algorithm`, `key_id`, signature over the canonical envelope excluding the signature field.

The envelope must distinguish missing, null and unknown values; impose bounds on vector cardinality, timestamp range, identifier sizes and causal-parent count; reject duplicate fields; and use the accepted cross-language canonical encoding profile. The canonical encoding decision remains coupled to the open polyglot wire-protocol decision; this document does not silently select CBOR or JSON.

## 4. Time models and their permitted uses

### 4.1 Wall-clock time

Wall-clock time is descriptive and useful for human display, external deadlines and correlation with independently timestamped systems. It is not a trusted ordering primitive. Store the source and uncertainty of every relevant clock reading. A timestamp with unknown clock quality must remain explicitly untrusted.

### 4.2 Monotonic time

Use a monotonic clock for elapsed durations, local timeout measurement and lease countdown while a process/device remains in the same boot/time domain. Monotonic values are not portable between devices or reboots and must never be compared as global timestamps.

### 4.3 Hybrid logical clocks and causal context

Use HLC as a practical sortable event label that combines a physical-time estimate with a logical counter. On receiving an event, advance the local HLC according to the defined merge algorithm. Preserve node identity and clock-quality metadata. HLC does **not** create consensus, prove truth, grant authority or replace explicit causal parentage.

For operations where causal relationships matter, carry explicit parent IDs or a bounded version vector. If event A is a prerequisite of B, B must identify A (or its committed version) as a causal dependency. A later wall-clock timestamp alone cannot establish A before B.

### 4.4 Authority time and secure expiry

Credential and lease expiry must be evaluated against an issuer/authority-controlled time basis with a declared maximum skew and bounded offline grace. Local monotonic timers can enforce a countdown after a trusted lease is accepted, but a client-supplied `now` value cannot renew or extend it. Clock rollback, reboot without a trusted monotonic anchor, missing time attestation or excessive skew moves the relevant authority domain to `TIME_UNCERTAIN`; privileged actions fail closed.

A signed time statement may attest that an authority issued a bounded time interval; it does not prove that the local device clock is correct. The design must tolerate time-source outage without silently granting indefinite credentials.

## 5. Version authority and causal commit

A single global total order for every event is unnecessary and would create a central bottleneck. Use scoped authority domains and per-aggregate sequencing:

- Each mutable aggregate has one logical write authority at a time, or a formally specified quorum/consensus protocol.
- The authority issues monotonically increasing `aggregate_sequence` and `authority_epoch`.
- Writes carry `base_version`; commit uses compare-and-swap against the authoritative current version.
- A lease holder must present a fencing token/epoch. Every write boundary rejects tokens older than the highest accepted epoch.
- A region or replica may accept local append-only observations while disconnected, but cannot represent them as globally committed authoritative state.
- Conflict resolution is domain-specific. Never apply generic last-write-wins to identity, authorization, revocation, money, governance, irreversible device actions or verified evidence.

HLC and version vectors help detect ordering and concurrency. They do not replace consensus or a single-writer/fenced-lease rule for non-commutative state.

## 6. Temporal validity of authority, policy and revocation

Identity and authorization records require separate dimensions:

- issuer and subject;
- principal/device/workload binding and audience;
- policy and schema version;
- issuer epoch and revocation epoch;
- not-before / expiry interval;
- nonce and replay state;
- maximum offline age and permitted offline capability set;
- authority checkpoint and signature.

A disconnected node may use only a previously issued, signed, narrowly scoped offline grant until its predeclared offline deadline. It cannot infer that a grant remains valid merely because it has not received a revocation. When the revocation watermark is stale beyond the permitted bound, high-risk capabilities are denied. On reconnect, the node must reconcile authority epochs before privileged writes or network leases resume.

Revocation is monotonic within an authority epoch: an older snapshot cannot undo a later revocation. Key rotation and issuer replacement require explicit lineage and a trust-root transition, not timestamp comparison alone.

## 7. Memory, state and evidence: bitemporal semantics

Memory and evidence records need at least two temporal axes:

- **valid time:** when the fact/observation is claimed to apply in the represented world;
- **transaction time:** when NORYX7 received, admitted, corrected or superseded the record.

Also preserve capture time, source-reported time, ingestion time and verification time where distinct. Never overwrite an earlier fact to conceal correction: append a correction/supersession event linked to the prior record. A query must be able to ask both “what do we currently believe?” and “what did the system believe at decision time T?”

Evidence freshness is domain-specific. Each evidence class defines validity duration, revalidation triggers, clock requirements, source trust, calibration version and invalidation dependencies. A revoked key, superseded policy, expired specialist qualification, changed simulator calibration or corrected source observation must invalidate dependent conclusions where the dependency graph says they rely on that evidence. Integrity digest alone does not establish temporal validity or truth.

## 8. Offline and partition semantics

Offline execution is a local proposal/commit domain, not an automatic extension of global authority:

1. Capture the signed snapshot, authority epoch, policy version, revocation watermark, state base version and trusted time bounds.
2. Enforce the snapshot's maximum age using a rollback-resistant local anchor where available; if that anchor is lost or uncertain, restrict to safe read-only/local operations.
3. Give every local operation stable operation/attempt IDs and append-only local sequence.
4. Mark local results `LOCAL_COMMITTED_PENDING_RECONCILIATION`, not globally committed.
5. On reconnect, authenticate the peer, validate current epochs, deduplicate by operation/idempotency key and compare causal/base versions.
6. Obtain a signed acceptance, rejection or final effect/commit receipt. A transport ACK is not a commit.
7. Preserve conflict and supersession lineage; never silently replace a newer authority state with an offline snapshot.

Exactly-once delivery is not assumed. The protocol is at-least-once delivery plus stable idempotency, durable inbox/outbox, deduplication and explicit unknown-outcome reconciliation. Irreversible actions remain disabled offline unless a separate risk-reviewed offline authority contract explicitly permits them.

## 9. Cross-stream requirements (W01–W12)

| Stream | Temporal consistency obligation |
|---|---|
| W01 Identity/trust | Signed issuer time, principal/device audience, not-before/expiry, monotonic revocation epoch and bounded offline validity |
| W02 Runtime/orchestration | Causal operation/attempt/effect IDs; authoritative operation sequence; timeout is not proof of no effect |
| W03 Memory/state/recovery | Bitemporal records, journal namespace/epoch, monotonic sequence, replay watermark, snapshot lineage and conflict-preserving recovery |
| W04 Agent Fabric | Agent lease/qualification validity, heartbeat freshness bounds, signed result event and stale-agent fencing |
| W05 Routing/providers | Provider request idempotency, attempt timeouts, effect receipt time and explicit unknown-outcome reconciliation |
| W06 NEXUS/FRL/evidence | Source/capture/ingest/verification times, causal proof dependencies, freshness and invalidation propagation |
| W07 MIRROR WORLD | Model/calibration version and validity interval; simulation time separated from wall time and empirical event time |
| W08 Devices/browser/offline | Boot/monotonic domain, signed offline snapshot, bounded offline lease, reconnect epoch and safe clock-uncertain mode |
| W09 Security/crypto/audit | Key validity/revocation intervals, signed checkpoints, trusted-time provenance, replay windows and tamper-evident sequence |
| W10 Specialist intelligence | Credential/jurisdiction validity, evidence freshness, model version and decision-time qualification snapshot |
| W11 Global distribution | Region membership epoch, fenced leases, causal replication, quorum rules, partition and rejoin watermarks |
| W12 Economy/governance/impact | Ledger sequence, settlement effective/recorded time, immutable correction lineage, voting eligibility snapshot and impact measurement period |

## 10. Required system states and conflict outcomes

Introduce explicit temporal/consistency outcomes (proposal; names are normative only after ADR acceptance):

- `TIME_TRUSTED`, `TIME_DEGRADED`, `TIME_UNCERTAIN`;
- `CAUSAL_COMPLETE`, `CAUSAL_GAP`, `CAUSAL_CONFLICT`;
- `CURRENT_AUTHORITY`, `STALE_AUTHORITY`, `AUTHORITY_CONFLICT`;
- `LOCAL_PENDING_GLOBAL_COMMIT`, `GLOBAL_COMMITTED`, `REJECTED_STALE_BASE`;
- `EVIDENCE_FRESH`, `EVIDENCE_EXPIRED`, `EVIDENCE_INVALIDATED`.

These are not interchangeable with runtime success/failure. A task may execute successfully in a local environment while its global commit remains pending or rejected. A valid signature may accompany stale authority. A newer event timestamp may still be causally unrelated.

## 11. Conflict and partition policy

- Identity, revocation, policy, key status, financial postings, governance outcomes and physical actuation: quorum/single-writer fenced authority; no automatic CRDT merge.
- Append-only telemetry and independent observations: mergeable streams with source identity, causal metadata and duplicate suppression; late arrival remains late, not rewritten as contemporaneous.
- User preferences and explicitly commutative metadata: CRDT may be considered only after operation algebra, privacy, retention and deletion semantics are specified.
- Memory facts and evidence: preserve concurrent versions and provenance; use claim-specific adjudication, not last-write-wins.
- Global membership and capacity: lease and fencing authority distinct from health/heartbeat. A node's self-reported clock/health cannot renew its lease.

## 12. Recovery and replay contract

Recovery must load a signed checkpoint, verify journal integrity and schema version, validate authority epoch and revocation watermark, replay events in causal order where dependencies require it, detect missing sequence ranges, deduplicate event/operation IDs, and quarantine unresolved conflicts. A local replay watermark must never be promoted to a global watermark without authority acknowledgement.

Out-of-order events may be buffered within a bounded window. If a causal parent never arrives, dependent operations remain pending/indeterminate; they are not guessed into order. A checkpoint must declare covered stream, aggregate, sequence range, causal frontier, schema version, authority epoch, key ID and checkpoint time basis.

## 13. Acceptance criteria for the later integration/verification phase

No test is claimed as run. The later cross-language suite must include:

1. Wall-clock rollback/forward jump while capability or lease is active.
2. Clock skew beyond declared bound and complete time-source outage.
3. Device reboot invalidating monotonic continuity and offline snapshot age checks.
4. Delayed revocation arriving after a cached grant; stale epoch must be rejected.
5. Concurrent writes to the same aggregate in two regions; exactly one fenced authority may commit.
6. HLC equal physical times, counter overflow, node restart and out-of-order delivery.
7. Causal parent missing, duplicated, reordered or arriving after dependent event.
8. Offline snapshot replay, duplicate operation, stale base version and conflicting local/global updates.
9. Evidence correction/revocation invalidating downstream conclusions without erasing history.
10. Ledger settlement with effective time different from recorded time; no timestamp-based duplicate posting.
11. Python/Kotlin/Go/Rust canonical envelope equality and signature negative vectors.
12. Recovery from a checkpoint with missing, duplicated, stale and forked event ranges.

Each test must assert both allowed and denied behavior and retain signed test evidence tied to exact source/build/configuration digests. These criteria are future gates, not current validation.

## 14. Open decisions (not accepted)

- Select the canonical HLC representation and bounds, vector-clock strategy and causal-context truncation policy.
- Define trusted time statement issuer, maximum skew, offline grace, reboot handling and failure behavior.
- Select quorum/single-writer protocol and lease/fencing authority for each critical aggregate class.
- Define event-time, valid-time, transaction-time and evidence-freshness profiles per domain.
- Decide which low-risk data classes may use CRDTs and specify deletion/retention interaction.
- Define signed checkpoint cadence, external timestamp/anchor custody and cross-region recovery watermark.
- Align this contract with the still-open canonical wire encoding and distributed membership decisions.

All decisions remain OPEN. No ADR is accepted by this document.

## 15. Closure statement

This specification extends the architecture across W01–W12. It does not claim global clock synchronization, distributed consensus, trusted timestamping, durable global event ordering, production revocation propagation or cross-language interoperability exists today. The architecture remains incomplete until owners accept the decisions, source composition is implemented, and adversarial cross-platform tests validate the exact behavior. All W01–W12 remain PARTIAL.
