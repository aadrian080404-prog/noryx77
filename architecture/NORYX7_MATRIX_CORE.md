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

## 14. Initial executable slices

The current branch now contains several deliberately narrow reference components:

- `core/matrix_core.py`: opt-in contribution grants, aggregate local resource ceilings, reserved capacity, thread-safe local reservations and monotonic revocation generations.
- `core/matrix_membership.py`: in-memory admission/revocation state machine with per-node monotonic epochs and replay checks.
- `core/matrix_membership_durable.py`: SQLite-backed per-node membership epochs, nonce replay checks, owner-binding and revocation tombstones across process restarts. The verifier is injected; hardware attestation and multi-node consensus remain external.
- `core/matrix_grants.py`: SQLite-backed owner grants with monotonic generation compare-and-swap, immutable node/owner binding and fail-closed revocation that clears resource ceilings and workload permissions.
- `core/matrix_reservations.py`: SQLite-backed node-local reservations with atomic multi-process quota checks, restart recovery, release and generation reconciliation that drains persisted reservations. It still does not terminate OS processes; the local supervisor must do that.
- `core/matrix_scheduler.py`: deterministic placement proposal using eligibility and dominant resource utilization. `propose_placement_with_device_policy` also filters on owner-defined battery, thermal, power, network, energy and schedule policy. These inputs are advisory snapshots; the target supervisor must refresh sensors and reserve locally before dispatch.
- `core/matrix_data.py`: SHA-256 content manifest for chunked immutable objects and corruption/order detection. It is not encryption, erasure coding, replication, access control or a distributed object store.
- `core/matrix_twin.py`: deterministic virtual-time event queue plus a test network model for latency, reordering, link partitions and delivery-time drops. It is not a consensus simulator, clock-drift model, model checker or production network stack.
- `core/matrix_fencing.py`: in-memory single-resource fencing reference.
- `core/matrix_durable.py`: SQLite WAL/FULL local persistence adapter that atomically stores a resource epoch, version and tenant-scoped idempotency records across process restarts. It is still one local database, not distributed consensus or a replicated authority.
- `core/matrix_budget.py`: owner-controlled contribution guard for opt-in state, battery, temperature, power, network-use ceiling, weekly schedule and estimated energy. It is consumed by the device-budget-aware placement proposal, but remains advisory until the target supervisor rechecks live sensors and enforces OS-level limits.
- `core/matrix_ledger.py`: local SQLite double-entry journal using integer minor units, atomic balanced postings, tenant-scoped idempotency, an injected authorization verifier and a read-only integrity audit that detects extra/missing/mismatched postings. It is not a payment rail, custody system, cross-domain transfer protocol or compliance implementation.

These are executable slices, not a production distributed system. The original `LocalReservationBook` remains in-memory; `DurableReservationBook` adds node-local SQLite reservation recovery and multi-process serialization for one local database. Durable membership, grant, reservation, fencing and journal adapters survive ordinary process restarts when local SQLite storage honors its durability contract, but they do not coordinate multiple machines or establish global consensus. Device-budget scheduling is a policy filter over supplied telemetry, not trusted sensor enforcement. No module in this PR establishes cryptographic device identity, a secure sandbox, financial custody, production distributed storage, or planet-scale capacity.

## 15. Required next hardening

1. Define backup, corruption recovery, schema migration and a supervisor process-kill/drain contract. Durable membership epochs, owner grants, revocation tombstones and node-local reservations now have SQLite reference implementations.
2. Bind every admission proof to node identity, owner, software measurement, nonce, epoch and verifier policy; use hardware-backed attestation where available.
3. Enforce fencing tokens at the protected resource itself, atomically with each privileged write. A lease or coordinator-side check alone is insufficient.
4. Connect the device-budget-aware placement proposal to target-side fresh sensor checks, local atomic reservations and real OS/sensor enforcement; add network egress and data-residency controls.
5. Replace advisory in-memory placement with reserve-confirm-commit, idempotent retries and reconciliation after lost acknowledgements.
6. Add bounded membership storage, tombstone retention and safe identity re-enrollment procedures.
7. Extend the Digital Twin with clock drift, stale/duplicated messages, Byzantine behaviors, disk faults, correlated failures and deterministic seeded fault schedules. A first deterministic latency/partition/drop transport model is now present.
8. Add authenticated-manifest tests, storage encryption, key separation, erasure coding, replication and rate-limited repair as independent layers.
9. Extend the local ledger with account policy, append-only external audit anchoring, reconciliation, hash-chained audit proofs and a separately specified cross-partition transfer protocol; never expose it as real-money settlement.

## 16. Current implementation boundary

No component here should be described as production-ready or globally distributed. The code provides policy/state-machine foundations for further implementation and adversarial testing only.

## 16. Local supervisor integration slice

- `core/matrix_supervisor.py` composes durable membership, owner grants, device-budget policy and node-local durable reservations into one fail-closed admission/dispatch/revocation path.
- Dispatch rejects inactive membership, owner/node binding mismatches, stale local grant snapshots, disabled or stale grant generations, and device telemetry that is stale or from the future.
- A successful policy decision is followed by a durable local reservation before the executor adapter is invoked. If executor startup fails, the reservation is released.
- Revocation is persisted first, then local reservations are reconciled and cleared, and finally the executor is asked to stop the affected task IDs. Stop failures are returned explicitly; they are not reported as successful process termination.
- `core/test_matrix_supervisor.py` exercises the complete local path, stale/future telemetry rejection, startup rollback, revoked membership, owner revocation and failed-stop reporting.
- Dispatch re-reads the durable membership/grant authority after reserving capacity and releases the reservation if authority changed before executor start. This narrows cross-process revocation races; target-side fencing remains mandatory for the final atomic check at the protected resource.

**Boundary:** this is a local orchestration contract, not a production process supervisor. The executor must implement target-side generation fencing and sandboxing atomically. The current adapter is an interface/fake-test contract; no OS process kill, cgroup/job-object enforcement, hardware attestation, distributed consensus, or cross-machine revocation propagation is claimed. Telemetry freshness uses a caller-supplied monotonic clock domain.

## 17. Financial transfer and data-integrity integration slices

- `core/matrix_transfer.py` adds a local durable two-participant transfer coordinator. It records an immutable request digest, participant bindings, prepare acknowledgements, commit acknowledgements and terminal/recovery states.
- Retries require participant-side idempotent prepare/commit operations. A partial commit is retained as `IN_DOUBT`; recovery resumes missing commits and never claims completion until both participants confirm. Once commit begins, the coordinator does not attempt an unsafe compensating abort.
- `core/test_matrix_transfer.py` covers normal commit, idempotent replay, request conflicts, partial-commit recovery and participant-binding rejection.
- `core/matrix_data.py` now exposes `verify_authenticated_object`, requiring both a valid keyed manifest tag and a complete chunk/hash/object-ID verification before accepting the object.
- `core/test_matrix_data_integrity.py` covers tampering, invalid tags, reordered/missing chunks and invalid manifest types.

**Boundary:** transfer coordination is a local protocol journal, not a payment rail, custody service, distributed transaction manager or legal settlement. Participants need their own durable idempotency and atomic state transitions; coordinator/participant network partitions can leave transfers `IN_DOUBT` and require recovery. Data authentication is HMAC-based integrity/authenticity with externally managed keys; it is not encryption, key distribution, replica repair, erasure coding or proof of storage availability.


## 18. Durable resource-side fencing increment

- `core/matrix_fencing_durable.py` adds a SQLite-backed protected-resource reference. Epoch activation is strictly monotonic; each new operation checks the active token and records its idempotency result/version in the same `BEGIN IMMEDIATE` transaction.
- Operation IDs are scoped to a resource and bound to a SHA-256 payload digest. Repeated identical operations return the original receipt without repeating the state change; reusing an ID with different bytes is rejected.
- State survives process restart. Concurrent local writers serialize through SQLite and receive unique monotonic versions.
- `core/test_matrix_fencing_durable.py` covers restart, stale generations, replay/conflict behavior, resource isolation, concurrent writers and invalid timeout values.
- Idempotent retries are accepted only while their fencing generation is still current; a revoked generation cannot obtain a stale success receipt by replaying an earlier operation ID.

**Boundary:** SQLite serializes writers on one database host. This is not a cross-region consensus service, hardware-backed monotonic counter, OS-level process fence, payment execution adapter or proof against a compromised host. The executor must still call the protected resource's enforcement point; coordinator-side checks alone cannot close a time-of-check/time-of-use race.

## 19. Authenticated durable network inbox increment

- `core/matrix_inbox.py` adds a local SQLite inbox with HMAC-SHA-256 authenticated envelopes, explicit sender/recipient/message/key identifiers, expiry, bounded payload size, durable pending/delivered/expired states and recipient-scoped message deduplication.
- The caller injects trusted key IDs and key material. The signature binds sender, recipient, message ID, key ID, expiry and payload bytes. Replayed identical messages return their original receipt; conflicting reuse of a message ID is rejected.
- Delivery acknowledgement is a durable state transition; expired pending messages cannot be acknowledged as delivered.
- `core/test_matrix_inbox.py` covers authentication tampering, untrusted key IDs, recipient binding, expiry, replay conflicts, restart, delivery idempotency and payload limits.

**Boundary:** This is an inbox persistence/authentication slice, not a network socket, transport encryption, public-key identity system, distributed replay cache, key rotation protocol, guaranteed delivery or consensus layer. HMAC requires shared secret distribution and rotation to be designed separately. No message is delivered to an application until its caller explicitly consumes/acknowledges it.


## 20. Network identity and message handoff hardening

- Inbox key IDs are now explicitly bound to an authorized sender identity. A valid HMAC under a trusted key cannot be used to assert an arbitrary sender name.
- Envelope serialization uses length-prefixed fields, avoiding delimiter ambiguity in attacker-controlled identifiers.
- `read_pending(message_id, now=...)` returns the payload only while it remains pending and unexpired. The caller can retry processing after a crash and acknowledge only after its own processing succeeds.
- This is an **at-least-once handoff** contract. External side effects still need their own idempotency key; the inbox cannot promise exactly-once processing across a crash between the side effect and acknowledgement.
- Tests cover sender/key impersonation, payload retrieval/retry, expiry during read and complete key-to-sender configuration.

## 21. Digital Twin crash/restart and duplicate-delivery hardening

- `DeterministicNetwork` now schedules node crash/restart events and models delivery failure while either endpoint is unavailable.
- `send(..., copies=N)` can model bounded duplicate delivery (1–16 copies) with stable event ordering; the transport intentionally does not deduplicate because the receiver/inbox must prove replay safety.
- Drop traces distinguish `PARTITION` from `NODE_UNAVAILABLE`.
- Tests exercise duplicated message IDs, node crash, recovery and bounded fan-out.

**Boundary:** these are deterministic fault-injection primitives, not a physical network, process lifecycle manager or consensus implementation. Crash/restart events alter the simulator's availability model only.

## 22. Transfer journal hardening

- The local transfer coordinator now rejects non-finite database timeouts and closes SQLite connections deterministically, including exceptional paths.
- Its participant protocol remains at-least-once: prepare/commit adapters must be durable and idempotent. Concurrent coordinator instances can retry participant calls, so participant-side idempotency is mandatory.


## 23. Owner-scoped key policy registry

- `core/matrix_key_policy.py` stores durable key metadata only: key ID, owner, permitted purpose, monotonic generation and ACTIVE/REVOKED state.
- Secret bytes are never written to this registry. Key resolution calls an injected external provider only after owner/purpose/state and authorization checks.
- Key IDs cannot be rebound; generations increase per owner and purpose; revocation persists across restart and blocks later resolution.
- `core/test_matrix_key_policy.py` covers ownership/purpose isolation, monotonic rotation, revocation, authorization failure and invalid external key material.

**Boundary:** this is not a KMS, HSM, PKI, key backup service or cryptographic key-generation system. The external resolver must provide secure custody, rotation, backup and destruction. Authorization callbacks and key provider are trust boundaries.

## 24. Critical command two-person permit gate

- `core/matrix_safety_gate.py` persists proposals and distinct operator approvals for a narrowly scoped command digest and resource.
- The proposer cannot approve their own proposal. At least two distinct authorized operators are required; their authorization is rechecked when a permit is issued and consumed.
- The local safety interlock is checked both before issuing a one-time permit and again at the consumption boundary. Permits are resource/command/expiry-bound and cannot be consumed twice.
- `core/test_matrix_safety_gate.py` covers insufficient/duplicate approvals, proposer self-approval, authorization revocation, interlock denial, command/resource binding, expiry and one-time consumption.

**Boundary:** this gate issues/consumes authorization permits only; it never executes commands. It is not a certified safety controller, physical interlock or replacement for local protection. The actuator adapter must atomically validate the permit and enforce its own safety state at the actual actuation boundary. Operator identity must come from a trusted external authentication system.


## 25. Cross-component local end-to-end verification

- `core/test_matrix_end_to_end.py` composes durable membership admission, owner grant, device budget, durable reservation and supervisor dispatch with a resource-side SQLite fencing adapter.
- The same scenario exercises authenticated inbox acceptance, pending payload handoff, durable acknowledgement and duplicate-message receipt; it then completes a two-participant transfer through the durable transfer journal.
- Finally, owner revocation clears the local reservation and the test target advances its resource fence, proving that a late write carrying the old generation is rejected after revocation.
- The test is intentionally local and deterministic. The executor double models the target-side fence contract; it does not prove remote propagation, process termination, distributed consensus, real payment settlement or network availability.


## 26. Live key-policy enforcement at the inbox boundary

- DurableInbox can now resolve key material dynamically through an injected policy-backed resolver instead of retaining a static key snapshot.
- Sender-to-key binding is checked before resolution; the resolver can enforce owner, purpose, generation, authorization and revocation on every message acceptance.
- A regression test accepts a message, revokes its NETWORK_HMAC key in the durable policy registry, then proves the same inbox instance rejects a subsequent message.
- Dynamic key policy is rechecked when a pending payload is released, so a message accepted before key revocation is no longer readable afterward. This is a fresh policy check, not an atomic cross-database revocation transaction; deployment must define the policy registry as the key authority and bound the remaining check/use window.
- Existing static-key configuration remains supported for isolated tests and deployments that deliberately manage rotation outside the registry.

**Boundary:** the resolver callback and its owner/sender mapping remain trust boundaries. This change does not distribute revocation across machines or replace KMS/HSM custody.
