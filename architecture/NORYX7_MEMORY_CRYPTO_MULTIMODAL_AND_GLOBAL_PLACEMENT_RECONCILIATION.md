# NORYX7 — Memory Custody, Cryptographic Authority, Multimodal Lineage and Global Placement Reconciliation

**Review date:** 2026-11-24  
**Source snapshot:** `a6228caad56b68be0ff576749fc047efcda56199`  
**Scope:** architecture-only source reconciliation. No runtime, tests, dependencies, workflows, deployment or frozen baseline modified.

## 1. Purpose and interpretation

This pass examines the data and trust lifecycle from ingress through memory, encryption, key custody, multimodal references, agent identity, supply-chain admission and device/edge/cloud placement.

A primitive is not a complete service. In particular:
- encryption is not persistence;
- a digest is not source authenticity;
- a key state machine is not a KMS;
- an identity signature is not current authorization;
- a replica label is not a healthy replica;
- a resource tier decision is not capacity admission;
- a media locator is not consented, durable and retrievable media custody.

All claims below are bounded to the inspected source paths at the stated commit.

## 2. Memory and context custody

### 2.1 Observed source behavior

- `core/memory.py` provides a bounded in-process `MemoryStore`, deep-copy isolation, source/kind fields and optional execution_id filtering in `get/list`.
- `core/memory_hierarchy.py` defines L0–L5 levels and a bounded in-process key/value map. The record carries key, value and level only.
- `core/secure_memory.py` serializes a `MemoryItem` schema and delegates encrypted persistence to `EncryptedRecordStore`.
- `core/secure_storage.py` authenticates namespace and record ID as AES-GCM associated data and stores ciphertext in an in-process dictionary. The source explicitly expects a production backend adapter.
- `core/context.py` calls `memory.list()` without passing its optional execution_id, then filters by `source == task_id`. Memory-list exceptions are converted to an empty tuple, indistinguishable from no matching memory. The returned context can therefore omit execution isolation and hide degraded hydration.
- `jarvis/memory/store.py` is a separate bounded in-process dictionary with no execution, tenant, provenance, retention or deletion contract visible in the inspected class.
- `ecosystem/global_fabric.py` stores record metadata/digests and replica labels in an in-process index; it does not retain the payload bytes in this index. `require_redundancy` counts labels, not healthy/reachable/durable independent copies.

### 2.2 Required canonical memory envelope

Every persisted or shared memory item needs:
- immutable record ID, schema version and content digest;
- tenant, principal, agent, task, execution and session scope;
- source class (user-provided, observed, retrieved, generated, inferred, tool-produced);
- source references and transformation/derivation lineage;
- purpose, consent/legal basis and permitted processing operations;
- sensitivity/data classification and residency constraints;
- creation, observation, valid-from, expiry and retention timestamps;
- encryption key ID/version and authenticated namespace;
- access policy, sharing scope and disclosure history;
- deletion request, tombstone, propagation and legal-hold state;
- replica identities, health, consistency watermark and restore evidence.

Context hydration must return a typed outcome: `COMPLETE`, `EMPTY`, `PARTIAL`, `STALE`, `DENIED`, `UNAVAILABLE` or `CORRUPT`. A failed memory read must never silently become a normal empty context. An execution-scoped request must pass the execution ID into the storage query, not filter only after a global listing.

### 2.3 Memory lifecycle and deletion

Define separate lifecycle states for working, session, task, long-term, shared, archival and suspended memory. Promotion between levels is a policy-controlled data movement, not just a level integer update. Deletion must cover primary payload, indexes, embeddings, derived caches, replicas, backups and exported references, with tombstones and auditable completion evidence. Cryptographic erasure is only valid when all relevant copies and keys are within the declared erasure boundary.

## 3. Cryptographic authority and key lifecycle

### 3.1 Observed source behavior

- `core/crypto.py` uses AES-256-GCM and HKDF-SHA256 with domain-separated subkeys, key IDs and authenticated metadata.
- `InMemoryKeyProvider` is explicitly test-oriented; `KeyProvider` is an external boundary.
- `core/key_lifecycle.py` models ACTIVE, RETIRING and REVOKED key metadata and exposes an `ExternalKeyBoundary` interface. The inspected manager stores key records in a local dictionary; no external KMS/HSM adapter or durable consensus is established by this class.
- `core/attestation.py` delegates attestation verification to an external verifier and binds runtime ID, measurement, nonce and expiry locally. Durable nonce replay protection, remote revocation and attestation trust-root lifecycle remain external.
- `core/identity.py` provides Ed25519 agent identity/attestation primitives and an in-process trust-anchor registry.
- `core/supply_chain.py` verifies Ed25519-signed artifact manifests and artifact digests against a locally supplied trusted-key set. The manifest contains component ID, version, artifact digest, signer key and signature; no signer role, key validity interval, revocation epoch, SBOM/build provenance or release approval is represented in that manifest.

### 3.2 Required key authority model

Separate:
1. root trust anchors and offline recovery authority;
2. KMS/HSM key generation and non-exportable key custody;
3. data-encryption key (DEK) wrapping and envelope encryption;
4. key derivation context and namespace separation;
5. key version, activation, rotation, retirement and revocation;
6. signer identity, role, purpose, artifact scope and release authority;
7. compromise response, emergency revocation and re-encryption;
8. backup/restore and disaster recovery of key metadata;
9. audit evidence and independent checkpointing.

Key IDs must be globally unambiguous within the authority domain. Rotation must specify how old ciphertext is read, rewrapped or re-encrypted, how mixed-version replicas converge and how revoked keys are denied across offline nodes. A local ACTIVE state must not override a newer remote revocation epoch. Trust roots require an explicit bootstrap and recovery ceremony; they cannot be self-authorized by the runtime they attest.

## 4. Multimodal data custody and evidence lineage

### 4.1 Observed source behavior

`core/multimodal.py` defines modality, content type, SHA-256 digest and locator. `MediaRef.create` hashes supplied bytes but retains only a locator reference in the record. `MultimodalInput.build` hashes the ordered references into a request digest.

The contract does not itself establish:
- locator authentication, authorization or expiry;
- encrypted payload storage and transport;
- consent/purpose and sensitive-data classification;
- retention/deletion propagation;
- source identity, capture device, capture time or chain of custody;
- transformation lineage (crop, transcode, OCR, ASR, embedding, summary);
- model/tool version and parameters for derived artifacts;
- integrity of retrieved bytes at every later read;
- provenance of timestamps, geolocation or metadata.

A digest can detect a mismatch against known bytes; it cannot prove who captured the media, whether the locator is trustworthy, or whether the content is true.

### 4.2 Required media artifact graph

Represent original media and every derivative as immutable linked artifacts. Each node records content digest, encrypted object reference, media type, schema, source/capture provenance, consent, classification, retention, transformation operation/version, parameters, parent artifact IDs and output digest. Access to a locator is capability-scoped and time-bounded. The retrieval boundary verifies digest after fetch and before decode. Derivatives inherit restrictions unless a documented policy permits a narrower or broader use.

Separate evidence observations from model interpretations. OCR text, speech transcripts, image captions, embeddings and inferred entities must not be silently promoted to original-source facts.

## 5. Agent identity, skill and execution model

### 5.1 Observed source behavior

- `core/agent_core.py` models a single agent lifecycle and executes plan steps sequentially under a local lock. The authorization hook is optional; if omitted, the core itself does not reject a step on authorization grounds.
- `core/agent_fabric.py` checks identity registry trust and a principal authorization callback, then iterates bindings in sorted ID order and dispatches to the first authorized candidate. It does not rank by live health, capacity, queue, locality, cost, energy, domain qualification or independent failure domain.
- `core/agent_skills.py` explicitly states that skills describe capabilities and do not grant authority. A default declarative skill handler is a no-op.
- `core/agent_identity.py` supplies a shared immutable mission charter, not a per-agent scoped operational grant.

### 5.2 Required agent admission and placement

Separate agent identity, mission charter, skill declaration, specialist qualification, current runtime attestation, principal delegation and action authorization. Each agent binding must declare:
- signed artifact/build identity and version;
- skill and domain scope with qualification evidence and expiry;
- allowed data classes, jurisdictions and residency;
- resource profile, hardware/runtime constraints and safety envelope;
- health lease, queue depth, current capacity and degradation state;
- model/provider/source lineage and independence group;
- maximum delegation depth, action scope, budgets and deadline;
- revocation epoch and audit correlation.

Selection is a constrained admission problem, not first-match iteration. An unavailable or unhealthy agent is excluded; a capability match is not sufficient if its data residency or authority does not match. Consensus independence must consider shared models, providers, datasets, operators, keys and failure domains.

## 6. Global scale and resource placement

### 6.1 Observed source behavior

- `core/resource_router.py` chooses DEVICE/EDGE/CLOUD using fixed complexity, privacy and latency thresholds.
- `ecosystem/global_scale.py` defines bounded Region/Cell, capacity, health, degradation, queue and metric primitives. Its module documentation explicitly states these are control-plane models, not a cloud provider, database, scheduler or network fabric.
- `ecosystem/global_fabric.py` provides local memory metadata and replica labels, not production distributed storage or replica health proof.
- The inspected classes do not establish a durable distributed scheduler, workload broker, cross-region consensus, cloud autoscaling or production telemetry backend.

### 6.2 Required placement decision

Every placement decision must consider:
- capability and minimum hardware/runtime requirements;
- current measured capacity, queue, health and admission reservations;
- latency/deadline and availability target;
- privacy class, jurisdiction and data residency;
- provider and region trust/attestation;
- estimated monetary cost, energy/carbon intensity and resource scarcity;
- local/offline constraints and synchronization cost;
- redundancy/failure-domain requirements;
- deterministic reproducibility and model/runtime version;
- policy constraints and fallback equivalence.

Placement output must include a decision ID, candidate set, rejected-candidate reasons, measurements and freshness, policy version, reservation/lease, expected cost/energy, data movement and fallback plan. Capacity must be reserved atomically or revalidated at dispatch; stale telemetry must not be treated as current capacity.

## 7. Supply-chain and operational assurance

The artifact manifest currently binds component/version/digest to a trusted signer key. The production architecture must add:
- SBOM and dependency graph;
- source revision and build recipe;
- reproducible-build or independent build attestation;
- build environment identity and provenance;
- signer role, approval quorum and key validity/revocation;
- vulnerability/advisory status and exception expiry;
- firmware/model/dataset provenance where applicable;
- staged rollout, health gates, rollback and emergency revocation;
- cross-platform compatibility matrix for Python, Go, Rust, Kotlin, Swift and web surfaces.

Observability and event publication require durable storage, sequence ownership, retention, alert routing and incident response. A bounded in-process event buffer is not an operational monitoring platform.

## 8. Cross-workstream reconciliation

| Workstream | New source finding | Required closure | Status |
|---|---|---|---|
| W01 Identity | Agent trust, runtime attestation, key trust and principal delegation are distinct local registries/interfaces | Canonical issuer, tenant/session/device, agent signer, attestation and revocation epochs | PARTIAL |
| W02 Runtime | AgentCore sequential local lifecycle; storage and key state are separate in-process stores | Unified execution, context, persistence and recovery lifecycle | PARTIAL |
| W03 Memory | Context hydration omits execution_id at list call; encrypted storage remains in-process; L0–L5 hierarchy has minimal schema | Scoped memory envelope, typed hydration, durable adapters, deletion/retention and lineage | PARTIAL |
| W04 Agent Fabric | First authorized sorted agent selected; skills are descriptive; local lock serializes one AgentCore | Qualified agent admission, health/capacity placement, delegation and independence groups | PARTIAL |
| W05 Routing | DEVICE/EDGE/CLOUD selected by static thresholds | Live capacity, cost, energy, latency, residency and trust-aware placement | PARTIAL |
| W06 Evidence | Media digests do not establish capture provenance or truth; derivatives not represented as a lineage graph | Immutable artifact graph, signed source receipts and transformation lineage | PARTIAL |
| W07 MIRROR WORLD | Multimodal inputs and model artifacts lack a unified custody/validity binding | Snapshot, media, model, parameter, calibration and experiment provenance | PARTIAL |
| W08 Surfaces | Device/browser/edge/cloud media and memory references lack one shared custody lifecycle | Cross-surface encryption, locator authorization, offline sync and deletion propagation | PARTIAL |
| W09 Security | AES-GCM/Ed25519 primitives exist; trust/key registries need external authority and revocation | KMS/HSM, root ceremony, key epochs, hardware attestation and compromise recovery | PARTIAL |
| W10 Domains | Skill labels and domain names do not prove specialist qualification | Qualification evidence, scope, expiry, domain validators and independent review | PARTIAL |
| W11 Operations | Global scale, observability and supply-chain classes are bounded local primitives | Durable broker/storage/telemetry, SLO, DR, release provenance and staged rollout | PARTIAL |
| W12 Ecosystem | Global resource placement affects community projects, energy use and environmental outcomes | Transparent cost/energy/residency accounting and independent outcome evidence | PARTIAL |

## 9. Existing ADR mapping — no duplicate series

Consolidate these findings into existing open decisions:
- B70/B72/B77: durable audit, artifact provenance and evidence-backed release/freeze;
- B71/B73/B74: enforced egress, offline trust and durable delivery;
- B76/B78/B99: specialist qualification and independent self-improvement admission;
- B81/B103: memory custody, isolation, deletion and degraded-context semantics;
- B82/B102: identity issuer, key/session/device freshness and revocation;
- B85/B87: agent dispatch ownership, scheduling, leases and capacity;
- B90/B94/B97: evidence assurance, multimodal custody and claim lineage;
- B92/B93/B100: temporal/domain model validity and MIRROR WORLD evidence;
- B95: production adapter and provider boundary;
- B101: environmental/community outcome accounting;
- B104: durable outbox and uncertain effect reconciliation.

Do not create parallel memory, key, placement or evidence authorities. Each cross-cutting contract must identify one owner and explicit adapters.

## 10. Closure status

W01–W12 remain PARTIAL. This pass documents source-level boundaries and target contracts only. It does not add a production KMS, durable database, object store, broker, scheduler, replica protocol, attestation service, media custody service, observability backend or release pipeline. No tests, CI pass, deployment readiness or architecture freeze are claimed.
