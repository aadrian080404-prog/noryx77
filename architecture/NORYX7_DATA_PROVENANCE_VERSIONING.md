# NORYX7 — Data, Provenance, Semantic Versioning and Offline Trust Architecture

**Status:** architecture proposal; schemas and adapters are not implemented by this document  
**Scope:** NEXUS, knowledge/evidence, memory, multimodal lineage, tenant isolation, compatibility and offline trust.

## 1. Unified artifact model

All data-bearing subsystems use a shared conceptual artifact envelope, with domain-specific payload schemas:

- artifact ID and artifact kind;
- schema ID/version and vocabulary/ontology version;
- producer principal/agent/runtime identity references;
- tenant and access scope;
- creation time and valid-time interval;
- source artifact references;
- transformation lineage;
- epistemic status;
- data classification and permitted purpose;
- integrity digest and optional signature reference;
- retention/expiry/deletion policy;
- resource/size limits.

This envelope is a conceptual contract. NEXUS-IR, Evidence Registry, Memory, Audit and Wire adapters may use different physical encodings but must preserve these semantics at their boundaries.

## 2. Source, claim and evidence distinctions

A source artifact is not the same as a claim extracted from it; a claim is not the same as an assessment; an assessment is not the same as a proof or observation.

Canonical chain:

`SOURCE → EXTRACTED CLAIM → NORMALIZED CLAIM → EVIDENCE ITEM → DOMAIN ASSESSMENT → SYNTHESIS → USER-FACING STATEMENT`

Each edge records the transformation, actor/tool/version, source coordinates, timestamp and lossiness. A user-facing statement must retain links to the underlying claim/evidence set.

Epistemic states:
- observed;
- source-reported;
- derived;
- formally proven;
- simulated;
- hypothesized;
- disputed;
- unsupported;
- unknown;
- expired.

No automatic promotion based solely on model confidence, repetition, majority vote, cryptographic signature or storage in memory.

## 3. NEXUS semantic model boundary

NEXUS-IR defines typed semantic nodes, relations, quantities, events, goals, constraints, claims and evidence references. It must not conflate:
- missing versus unknown versus not applicable;
- zero versus absent measurement;
- observation versus report versus inference;
- time of observation versus time of validity;
- correlation versus causal relation;
- physical quantity versus unitless number;
- formal proposition versus natural-language claim;
- executable command versus descriptive action concept.

Ontology terms are versioned and governed. Unknown required types/relations fail closed. Optional extension fields may be preserved only under an explicit compatibility profile and cannot alter authorization semantics.

## 4. Canonicalization and digest policy

Canonicalization is versioned and explicit:
- Unicode normalization profile is named;
- duplicate map/object keys are rejected;
- key ordering is deterministic;
- numeric representation is constrained and non-finite values rejected;
- units and dimensions are normalized only under declared conversion rules;
- timestamps include timezone/offset and precision policy;
- absent/null/unknown/not-applicable remain distinct;
- references are stable and validated;
- collection order is preserved where semantically meaningful and canonicalized only where schema declares set semantics;
- maximum depth, item count and payload bytes are enforced.

Digest/signature domains are separated by artifact type, schema version and purpose. A cryptographic digest identifies bytes under a canonicalization profile; it does not prove semantic equivalence or truth. Semantic equivalence requires a domain-specific, versioned equivalence relation and evidence.

## 5. Versioning and compatibility

Every schema/vocabulary has:
- stable identifier;
- semantic version;
- compatibility class;
- deprecation window;
- migration transform and provenance;
- test vectors and known unsupported features;
- owner/reviewer and release record.

Compatibility rules:
- patch: correction that preserves declared semantics and wire compatibility;
- minor: additive optional fields/terms under a declared extension policy;
- major: incompatible meaning, required fields, relation semantics or canonicalization changes.

Unknown major versions are rejected. Unknown required fields/relations are rejected. Optional extension handling is explicit and cannot create executable authority. Downgrade is prohibited when it discards security, provenance or epistemic fields.

## 6. Memory and knowledge lifecycle

Memory lifecycle:
`CANDIDATE → PROVENANCE_CHECKED → POLICY_ADMITTED → STORED → INDEXED → RETRIEVED → REVALIDATED → EXPIRED/DELETED/QUARANTINED`

Memory admission checks:
- source and producer identity;
- permitted purpose and retention;
- tenant/execution scope;
- poisoning indicators and conflicting provenance;
- data classification and minimization;
- size and resource limits;
- schema/vocabulary support.

Retrieval returns evidence references and freshness state, not a blanket assertion of truth. High-impact claims are revalidated against current sources. Memory cannot authorize tools or actions.

Deletion:
- deletion request creates a tombstone and retention event;
- active indexes, caches and replicas receive deletion propagation;
- offline replicas carry expiry/reconciliation constraints;
- backups follow a documented expiry schedule;
- legal/security retention exceptions are explicit, access-controlled and auditable;
- restored snapshots must apply newer tombstones before making data visible.

## 7. Tenant and principal isolation

Isolation is enforced across:
- ingress and session state;
- context and prompt assembly;
- agent dispatch and tool execution;
- memory and vector/index stores;
- files, caches and temporary artifacts;
- audit query views;
- distributed replicas and offline snapshots;
- billing/metering and operator views.

A tenant ID is not a substitute for principal identity. Every read/write operation checks principal, tenant, execution, purpose and resource scope. Cross-tenant aggregation requires explicit policy and de-identification controls where appropriate.

## 8. Multimodal lineage

For image/audio/video/document/spatial/sensor inputs:
- retain original artifact or immutable source reference;
- preserve source coordinate system and timestamps;
- derived OCR/transcription/frame extraction is labeled derived;
- every extracted span/frame/sample points to source coordinates;
- transformations record tool/model/version and confidence;
- lossy compression/resampling/translation is declared;
- units, coordinate frames and synchronization assumptions are explicit;
- unsupported modality conversion returns unsupported/indeterminate, not fabricated content.

## 9. Offline trust and revocation

Offline nodes operate with a signed, bounded policy snapshot and trust epoch:
- snapshot issuer, policy version and creation time;
- maximum offline age;
- principal/device/agent revocation epoch;
- allowed action classes while disconnected;
- prohibited high-impact/irreversible actions;
- local capability expiry;
- sequence/nonce windows;
- sync and conflict resolution rules.

If revocation freshness expires, the node transitions to restricted mode. It may perform only predeclared low-risk/local operations that do not require fresh global authorization. It cannot silently route to cloud. Reconnection requires mutual authentication, epoch comparison, replay protection, journal reconciliation and tombstone application.

## 10. Data residency and egress

Every artifact has a classification and permitted processing locations. Placement decisions consider:
- source jurisdiction and residency;
- user consent and purpose;
- encryption/key custody;
- model/provider data handling;
- retention and deletion;
- external egress and onward transfer.

A model route cannot override residency policy. Egress is an explicit capability with target allow-list, data classes, expiry and audit record.

## 11. Decision and verification requirements for later phase

The architecture freeze review must resolve:
- one canonical source/evidence schema shared by NEXUS, UIF and Mirror World;
- whether physical source artifacts live in content-addressed storage or external immutable references;
- canonical time/clock trust and temporal validity semantics;
- ontology namespace ownership and extension policy;
- deletion semantics for third-party provider copies and backups;
- offline maximum age by action risk class;
- tenant isolation proof boundaries across caches and agent contexts;
- digest algorithm/version migration and key rotation.

Later verification must test canonicalization vectors, cross-version compatibility, tamper and replay, provenance loss, tenant isolation, deletion propagation, offline expiry/revocation, multimodal source coordinates and downgrade resistance.

**Decision status:** proposed shared data contract. It is not frozen until the open questions above have explicit decisions and migration rules.
