# NORYX7 Matrix Core — architectural contract

Status: **proposed implementation baseline; not a production certification**  
Branch: `architecture/noryx7-matrix-core-2026-11-14`

## 1. Founding model: protected devices are part of the infrastructure

NORYX7 is a distributed system whose protected endpoints can optionally contribute compute, storage, bandwidth, sensing, or verification capacity. The collective device fabric is an infrastructure substrate; no single server is the system's indispensable "mother".

Three roles must never be conflated:

1. **Protected endpoint** — receives NORYX7 security, privacy, identity, and local-runtime services.
2. **Contributing node** — explicitly opts in to one or more resource pools, under user-visible quotas and revocable grants.
3. **Authority-bearing node** — is independently admitted to a narrowly scoped consensus, signing, policy, or recovery role.

Protection does not imply contribution. Contribution does not imply authority. A phone that contributes spare CPU must not gain access to another user's data, global secrets, payment keys, or update authority.

## 2. Matrix invariants

- **No mandatory global coordinator:** local safety and eligible local work continue during WAN partitions.
- **No implicit resource consent:** contribution is opt-in, scoped, quota-bound, visible, revocable, and defaults off.
- **No data access by virtue of compute:** remote work receives only explicit, minimized, encrypted task inputs; never a general mount of a user's device.
- **No node self-certification:** execution, authorization, attestation, and audit are separate trust roles.
- **No global quorum for ordinary local operations:** consensus is partitioned by data/authority domain.
- **No silent split-brain writes:** each authoritative partition has a single fenced epoch/lease or a consensus protocol with documented safety assumptions.
- **No unbounded work:** queues, retries, task duration, memory, CPU, egress, and recovery traffic are budgeted.
- **No unsafe failover:** stale or partitioned nodes cannot continue privileged writes after losing authority.
- **No hidden loss of availability:** if safety cannot be established, reject or defer the operation and preserve recoverable state.
- **No claimed scale without measurement:** capacity claims require reproducible benchmarks across independent failure domains.

## 3. Node roles and control planes

### Local node supervisor
Runs on every participating node. Monitors local health and quotas, enforces local policy, isolates workloads, revokes expired capabilities, and supports safe offline behavior. It must not need a global round trip for local containment.

### Domain coordinator
Coordinates a bounded administrative/geographic/workload domain. It manages placement, membership, replication and recovery within its scope.

### Federated policy plane
Distributes signed, versioned policy and protocol changes. It does not schedule every task or authorize every payment. Policy updates require threshold approval, staged rollout, compatibility checks and rollback.

The network is not a three-tier command hierarchy. Coordinators are replaceable services with limited, explicit authority. Nodes validate signed state transitions and reject stale epochs.

## 4. The distributed device fabric

A node advertises only authenticated, measured capabilities and resource envelopes. Scheduling considers:
- explicit consent and revocation state;
- CPU, accelerator, memory, storage, bandwidth and energy budget;
- current load and reserved recovery headroom;
- trust/attestation state and software measurement;
- failure domain and administrative owner;
- data classification, locality and residency;
- task deadline, priority and cancellation;
- cost and network transfer required.

A task is eligible only when all constraints are met. Resource reservation is atomic within the local scheduler. Reservations expire or are released on cancellation/completion. A node must not overcommit the reserve required to survive its declared failure envelope.

### Contribution privacy boundary
Default contribution profile: **off**. A user may enable separate compute/storage/bandwidth pools. Each grant states maximum resource use, eligible workload classes, schedule, expiry, data-access policy and revocation behavior. NORYX7 must expose pause/revoke controls and stop accepting new work immediately after revocation; already-running work is terminated or safely drained according to the grant.

Sensitive personal data remains local by default. Compute-near-data is preferred; when remote execution is needed, use minimized task-scoped inputs, encryption in transit/at rest, isolated execution and explicit user/domain policy.

## 5. Partitioning and consistency

Use different consistency models for different data:
- strongly consistent, quorum-backed state for money, identity roots, authorization epochs and ownership;
- causally ordered or conflict-free replicated state only where domain semantics explicitly permit merges;
- eventual consistency for telemetry, discovery, non-authoritative indexes and cache refresh;
- immutable content-addressed objects for artifacts and audit evidence.

Gossip is suitable for membership hints and telemetry dissemination, not as proof of payment authorization, ownership, or a durable commit.

Consensus groups are small, bounded, and tied to a failure domain. Classical BFT sizing (3f+1 replicas to tolerate f Byzantine replicas) is only valid under the protocol's network, synchrony, independence and key assumptions. It is not a universal guarantee and must not be used as a slogan.

## 6. Data fabric

- Partition by tenant, owner, asset, key range or workload domain according to access patterns.
- Replicate hot/critical mutable state across independent failure domains.
- Use erasure coding for large immutable/cold objects where reconstruction cost is acceptable.
- Verify content with cryptographic hashes/Merkle proofs and authenticated metadata.
- Encrypt each data class with separate keys and least-privilege access.
- Maintain retention, deletion, legal hold and data-residency policy as first-class metadata.
- Run repair traffic under a budget so recovery cannot saturate the live system.
- Test correlated failures: replicas in one building, provider, power grid or administrative account are not independent.

## 7. Financial Integrity Fabric

The financial subsystem is isolated from AI planning and general-purpose task execution. AI can propose; a deterministic policy engine and independent authorization path decide.

Required properties:
- integer minor units and explicit asset identifiers;
- double-entry postings and balanced journal transactions;
- unique idempotency keys with durable deduplication;
- append-only authenticated audit trail;
- per-account/asset partitioning and explicit cross-partition transfer protocol;
- durable prepare/commit/recovery states and fencing against stale writers;
- independent key custody, limits, sanctions/compliance hooks and reconciliation;
- offline spending only against preallocated, bounded, cryptographically verifiable value.

No disconnected partition may mint spendable value or spend the same allocation twice. Any unresolved transfer remains visibly pending/restricted until deterministic reconciliation. This repository's current Matrix code does **not** implement a payment ledger or custody system.

## 8. Security and critical infrastructure

Treat every node, including a home edge server, as potentially compromised. Use hardware-backed keys/attestation where available, short-lived capabilities, revocation, measured boot, sandboxing, network segmentation, signed updates, independent audit and offline recovery.

Critical infrastructure integration is read-only by default. Local safety controllers must remain safe without NORYX7 connectivity. Write actions require domain-specific interlocks, independent authorization, bounded commands, operator procedures and tested rollback/safe-state behavior. NORYX7 must not replace certified safety systems.

## 9. Resilience and overload control

Each node/domain implements:
- admission control and bounded queues;
- per-tenant and per-priority quotas;
- backpressure and load shedding;
- deadline propagation and cancellation;
- bounded retries with jitter and retry budgets;
- circuit breakers and bulkheads;
- reserved recovery capacity;
- rate-limited repair/rebalance;
- progressive deployment and rollback;
- local operation during permitted network partitions.

Priority order is policy-defined. Life/safety and integrity-preserving operations are not displaced by analytics, model training, indexing or speculative agents.

## 10. Novelty: capability leases + resource escrow

Matrix's scheduling primitive is a **resource lease**, not an unbounded "available node" flag. A lease binds:
- node identity and attested software epoch;
- task digest and workload class;
- exact resource ceilings;
- data scope and egress policy;
- start/deadline/expiry;
- cancellation and revocation generation;
- placement/failure-domain constraints.

The node enforces the lease locally. The coordinator cannot expand it after issuance; an expanded task requires a new authorization. Leases are fenced by monotonically increasing generations so stale coordinators cannot revive revoked work.

For scarce resources, reserve capacity locally before advertising it to the domain. This prevents two coordinators from allocating the same CPU/storage/bandwidth envelope during a partition. Domain-level placement is advisory until the node confirms its reservation.

## 11. Verification strategy

A deterministic discrete-event simulator should model node clocks, message delay/reordering/loss, partitions, restarts, stale epochs, disk faults, correlated provider failures, malicious peers, and recovery storms. Every run records a seed and event trace so failures can be replayed.

Required properties to test:
1. resource use never exceeds an accepted lease;
2. revoked/expired generations cannot start new work;
3. user data is inaccessible without an explicit data grant;
4. partitioned nodes cannot perform fenced privileged writes;
5. local safe operation does not depend on global coordinator availability;
6. recovery traffic respects reserved budgets;
7. financial state transitions (when implemented) preserve per-asset conservation;
8. no rollout advances when verification or independent approval is absent.

## 12. Hardware roadmap: capability, not brand lock-in

Hollow-core fiber, conventional fiber, 5G/6G, Wi-Fi, satellite and Ethernet are transport options selected by measured latency, availability, cost, geography and threat model. Faster transport does not itself prevent interception or timing attacks; authenticated encryption, key management, routing diversity and physical security remain necessary.

Spintronic MRAM/PUF devices may become useful hardware roots or low-power memory/identity accelerators after independent characterization and supply-chain review. A PUF is not automatically unclonable or a complete key-management system; helper data, environmental drift, side channels, enrollment and revocation need analysis.

PS3/PS5/PSP hardware can be studied as constrained volunteer/edge compute only after verifying current toolchains, supported cryptography, isolation guarantees, power, network, firmware integrity and operational cost. Legacy PSP cryptographic primitives are not suitable as modern security foundations. Game-console compression blocks are not generic NORYX7 APIs. No device is trusted solely because it is a console or has a hardware security feature.

## 13. Delivery gates

**Gate A — contract:** this document, threat model, failure model, invariants and ownership model reviewed.  
**Gate B — local prototype:** opt-in resource lease and local quota enforcement with adversarial tests.  
**Gate C — two-domain prototype:** authenticated node membership, fenced scheduling and partition recovery.  
**Gate D — storage:** replication/repair and deterministic corruption/recovery tests.  
**Gate E — financial:** separate ledger proof, independent security review and reconciliation tests.  
**Gate F — scale:** measured multi-region/provider benchmarks and chaos testing.  
**Gate G — critical infrastructure:** domain certification, safety engineering and human operational governance.

Passing a gate means only that its stated tests passed. It is not a claim of global scale, production readiness, or formal verification unless those artifacts exist.

## 14. Current implementation boundary

The companion `core/matrix_core.py` is a deterministic policy primitive for opt-in node contribution and local resource reservations. It is not a network protocol, consensus implementation, secure sandbox, storage engine, financial ledger, attestation system, or production orchestrator. These require separate implementations and independent verification.
