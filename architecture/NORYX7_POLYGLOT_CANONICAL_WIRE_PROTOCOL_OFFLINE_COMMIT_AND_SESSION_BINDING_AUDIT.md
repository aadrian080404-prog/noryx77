# NORYX7 — Polyglot Canonical Wire Protocol, Offline Commit and Session Binding Audit

**Review date:** 2026-11-28  
**Source-tree HEAD inspected:** `10f139a539b11d27df97f4c974b5175bf00afdcd`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Mode:** architecture-only source audit and normative proposal. No runtime, browser, test, dependency, workflow, deployment, frozen baseline or production configuration changed.

## 1. Executive finding

NORYX7 has several useful local primitives: Python canonical-JSON helpers, an SQLite WAL/FULL state journal, a durable monotonic snapshot anchor, authenticated-encryption adapters and short-lived HMAC browser sessions. They do not yet establish one interoperable cross-language wire protocol or an end-to-end remote-commit proof for offline synchronization.

The most consequential distinction is between:
- integrity of locally serialized bytes;
- authentication of the issuer and intended audience;
- authorization for the exact operation;
- durable local enqueue;
- remote acceptance of the exact operation and payload;
- verified remote effect;
- final state commit and deletion of the local outbox record.

These are separate claims. The current offline acknowledgement path can remove an outbox item after matching its execution ID and, optionally, comparing a remote state version with the operation's *base* state version. It does not consume a typed signed receipt binding the remote service, operation, payload digest, resulting state version and commit sequence. The queue and sequence are held in process memory in the inspected implementation.

## 2. Bounded source observations

### 2.1 Core contracts and serialization

- `core/contracts.py` (blob SHA `a75491921288cbea6f1759ead99f97c83cfdc43d`) defines Python dataclasses for TaskSpec, ActionSpec, VerificationResult and AgentResult. These are useful in-process types, not a wire-level schema registry. Nested `Any` and Mapping values have no common cross-language canonical representation here.
- `core/actions.py` canonicalizes supported Python values and serializes action fingerprints with `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. This is a local Python profile. It does not, by itself, specify duplicate-key rejection at parse time, numeric normalization, Unicode normalization, float edge cases, cross-language map ordering, unknown-field handling or compatibility semantics for Kotlin/Go/Rust peers.
- `core/state_journal.py` (blob SHA `4ea3419cb05a4edbb228966ea2584894197caa83`) serializes state commits with sorted compact JSON and SHA-256 digest; it uses SQLite WAL and synchronous FULL. The file explicitly leaves OS/filesystem protection to the application. The digest detects mismatch relative to stored bytes; it is not an issuer signature, authenticated journal chain or external checkpoint.
- `core/tool_protocol.py` (blob SHA `1c529fbbf5352469be8ab6633edc48113da8a3bf`) is a small Python in-process ToolSpec/ToolResult registry. It carries a free-form provenance string and has no schema version, audience, canonical bytes, signed receipt, operation/attempt identity or remote effect semantics.
- `noryx7_runtime/contracts.py` (blob SHA `9bb6632b214e8d9d3221c9ccf03ab6233209a184`) defines separate Intent, ExecutionContext, PlanStep, ActionEnvelope and Attestation types. Their fields overlap with, but are not interchangeable with, core TaskSpec/ActionSpec/AgentResult.

The existence of these contracts is not a defect. The unresolved issue is that no single canonical wire-level profile, versioning/compatibility policy and cross-language conformance proof was established by the inspected paths.

### 2.2 Offline queue and acknowledgement

- `core/offline.py` (blob SHA `6d0c5a76134fa679279406da1a514e628240debd`) defines OfflineSnapshot, OfflineExecution, SyncEnvelope and OfflineSyncQueue. The queue stores encrypted envelopes and a monotonic sequence in Python dictionaries/in-memory counters. It verifies payload/ciphertext digests and binds ciphertext AAD to execution ID.
- `OfflineSyncQueue.acknowledge(execution_id)` removes the record by ID.
- `OfflineRuntime.acknowledge_synced` locates a matching execution ID, rejects a conflict flag, optionally compares `remote_state_version` to `matching.execution.base_state_version`, then removes the queue item. It does not require a signed remote commit receipt, a remote resulting version distinct from the base version, target transaction ID, operation idempotency key, server sequence, receipt freshness or receipt replay protection.
- `reconnect(authenticated=True, channel_verified=True)` receives booleans from its caller. The inspected method does not itself bind those booleans to a cryptographically authenticated peer identity, audience, channel exporter or session nonce.
- `core/offline_adapters.py` (blob SHA `bcdd8210b71f60a5f07f50b8975798fdd8c6b6f3`) adapts local policy, output-presence verification and authenticated encryption. The verification adapter accepts non-empty str/bytes; this is a shape/presence check, not semantic proof of remote commit.
- `core/offline_anchor.py` (blob SHA `a130043ae7dff949b072ae97fd00137d8051d2ea`) persists a highest snapshot timestamp/ID in SQLite WAL/FULL and documents hardware-backed protection as a production recommendation. This anchor protects snapshot rollback under its storage assumptions; it is not a durable queue or remote commit ledger.

### 2.3 Local state journal and gateway session

- `core/state_journal.py` uses SQLite transactions, a unique execution ID, sequence checks and record digests. It is a useful durable local commit primitive, but the inspected schema has no explicit tenant/journal namespace, previous-record hash, signed external checkpoint, migration ledger or key-revocation evidence. These are design requirements to assess by data class, not an assertion that SQLite cannot be secured.
- `gateway/auth.py` (blob SHA `fa456172c99b183dcb2acd0ec99303ec540d2583`) issues HMAC-signed sessions after a shared bootstrap token and caller-provided `client_id`. The token has expiry and nonce, but the inspected verification path does not check a server-side session registry, device enrollment/attestation, audience, principal issuer, per-session revocation or one-time nonce use.
- `gateway/server.py` (blob SHA `b434cdbe118ecea48029adcd2c954fa1ac14461c`) exposes session creation and execution using the client ID from the token. This is a client label carried in a signed token, not independently established user/device identity.
- Existing browser and Android flows are documented in prior reconciliations; this pass does not claim that every deployed ingress has identical behavior. The bounded finding is that the inspected gateway session contract alone does not establish device-bound principal identity or centrally revocable session semantics.

### 2.4 Existing test scope

Inspected, not executed:
- `core/test_offline_snapshot_rollback.py` (blob SHA `80b855fb770ca6e0b6a45d12800e014208d50935`) checks stale snapshot and same-epoch rollback rejection. Its test cipher is a test stub and the authenticator returns True; it does not exercise process restart durability, remote commit receipts, queue crash recovery or receipt replay.
- `core/test_state_journal_integration.py` (blob SHA `3f16420b2470176d0db550f9b76e700d029bb38f`) checks a SQLite state commit survives close/reopen and rehydrates. It does not test tampering, signed external checkpoints, schema migration, key rotation or cross-language byte equivalence.
- `core/test_hypersynth_runtime_contract.py` (blob SHA `987a4731742aa014124f6192c8ff3c2a7110d715`) checks malformed/forged verifier outputs are rejected at the local runtime boundary; it is not a polyglot protocol conformance suite.

## 3. Proposed NORYX7 wire-protocol profile

Create one logical protocol authority with language-specific generated bindings/adapters, not independent handwritten interpretations of each record.

### 3.1 Envelope

Every inter-process record carries:
- `protocol_id`, `schema_id`, `schema_version`, `canonicalization_profile`;
- `record_id`, `record_type`, `issuer`, `audience`, tenant/namespace;
- `issued_at`, `not_before`, `expires_at`, trusted clock profile;
- `policy_epoch`, revocation epoch and replay nonce;
- `operation_id`, `execution_id`, `attempt_id`, parent/correlation IDs where relevant;
- payload digest, digest algorithm, signature algorithm, key ID and signature;
- classification, residency, retention and provenance references;
- typed lifecycle status and explicit unknown/partial/error outcomes.

Correlation IDs never substitute for authority. A digest never substitutes for issuer authentication or semantic validity.

### 3.2 Canonicalization decision must be explicit

Do not silently treat Python `json.dumps` as a universal signature format. Architecture must compare deterministic CBOR (including a precisely selected deterministic encoding profile) against a constrained canonical JSON profile. The chosen profile must define:
- UTF-8 validity and Unicode normalization policy (normalization must not silently rewrite opaque identifiers or signed payload bytes);
- duplicate object key rejection before object construction;
- map/object key ordering and allowed key types;
- integer bounds, decimal representation, negative zero and prohibition/handling of NaN and infinities;
- byte strings, timestamps, null, booleans and absent-vs-null semantics;
- canonical treatment of arrays and set-like collections;
- maximum nesting, field count and payload size;
- unknown critical vs non-critical fields;
- exact signature preimage, domain separation, algorithm agility and key ID binding.

Selection remains OPEN until Python, Kotlin, Go and Rust implementations pass the same published golden vectors and negative vectors. The canonical bytes, not each language's ordinary serializer output, are the signed object.

### 3.3 Schema evolution and compatibility

- Schema IDs are immutable; major versions may break semantics, minor versions add compatible fields only under declared rules, patch versions clarify constraints without changing wire meaning.
- Unknown critical fields cause rejection; unknown optional fields may be retained and forwarded only where safe.
- Adapters are explicit, versioned and loss-aware. A lossy downgrade must be marked and cannot preserve a signature over the original semantic object.
- State migrations are append-only migration events with source/target schema, tool version, input digest, output digest, operator/approval and rollback strategy.
- Never infer a missing security field from defaults. Missing authority, audience, expiry or nonce fails closed.

## 4. Offline synchronization as a commit protocol

### 4.1 Distinct durable records

Define:
- `OfflineOperationRecord`: stable operation ID, principal, action digest, target, idempotency key, base version and payload digest.
- `OutboxRecord`: durable encrypted payload, AAD context, sequence, schema/cipher version, key ID, enqueue receipt and retry state.
- `RemoteAcceptanceReceipt`: authenticated remote identity, accepted operation ID, payload digest, idempotency key, server transaction ID and accepted sequence.
- `RemoteCommitReceipt`: remote commit ID, operation and attempt IDs, exact payload/action digest, resulting state version, target effect ID, commit timestamp, server journal sequence, issuer/audience, signature and policy epoch.
- `ReconciliationRecord`: unknown outcome, query evidence, duplicate detection, final disposition and human resolution where needed.

### 4.2 Required state machine

`QUEUED_DURABLE → SENT → ACCEPTED_REMOTE → EFFECT_PENDING → COMMITTED_REMOTE → RECEIPT_VERIFIED → OUTBOX_TOMBSTONED`

Alternative states: `RETRY_SAFE`, `OUTCOME_UNKNOWN`, `CONFLICT`, `REJECTED`, `REVOKED`, `QUARANTINED`, `RECONCILIATION_REQUIRED`.

The outbox item is not deleted when the HTTP call returns 200, when a matching ID appears, or when the server merely accepts a request. Deletion/tombstoning is allowed only after validating a signed RemoteCommitReceipt that binds the exact operation, attempt, payload/action digest, remote target, final state version and server sequence. Retain a durable tombstone and receipt digest for replay detection and audit.

### 4.3 Idempotency and unknown effects

- A logical operation retains one idempotency key across retry attempts; each transport attempt has a distinct attempt ID.
- The receiver persists the idempotency key and payload digest before applying a non-idempotent effect.
- Same key + same digest returns the same committed receipt; same key + different digest is a conflict.
- Timeout after possible dispatch becomes OUTCOME_UNKNOWN. Query by idempotency key/operation ID; never blindly replay a non-idempotent action.
- Compensation is a new authorized operation linked to the original effect, not a deletion or rollback assertion.
- If the remote peer cannot provide a verifiable commit receipt, preserve the local outbox record and require reconciliation.

### 4.4 Durability and crash consistency

The outbox must survive process restart and power loss under a declared filesystem/storage threat model. Enqueue, sequence allocation and record insertion must be atomic. Receipt verification and tombstone insertion must be atomic. Recovery must detect missing sequence, duplicate operation, ciphertext tamper, stale key, partial write and schema mismatch. Replication must preserve operation identity and prevent two disconnected replicas from independently claiming a unique commit.

## 5. Session and device identity contract

A session is a bounded authentication artifact, not a permanent principal. The session protocol should bind:
- authenticated principal issuer and subject;
- enrolled device/workload identity and attestation freshness where required;
- audience/service and exact permitted surface;
- session ID, nonce, issued/not-before/expiry, policy/revocation epoch;
- authentication method/assurance and user-presence/consent requirements;
- permitted capabilities or a reference to separately issued capabilities;
- key ID/signature and server-side revocation handle.

A caller-supplied `client_id` may be a display label or correlation field, never the sole identity proof. Bootstrap credentials should be exchanged for short-lived, audience-bound sessions and should not create unrestricted device trust. Session revocation and key rotation must invalidate privileged use at the enforcement boundary. Offline sessions use bounded cached trust with explicit stale/revoked uncertainty; a disconnected node cannot claim instantaneous global revocation.

## 6. Cross-stream obligations

| Stream | Protocol and lifecycle obligation |
|---|---|
| W01 | Canonical principal, device, issuer, audience, delegation and revocation semantics |
| W02 | Stable operation/attempt identity, canonical action digest, unknown-outcome handling |
| W03 | Durable outbox, journal namespace, crash-safe tombstone and migration ledger |
| W04 | Agent results and delegations signed over canonical typed envelopes |
| W05 | Provider request/response, destination and idempotency contracts |
| W06 | Canonical source/claim/proof references; preserve semantic vs integrity verdict |
| W07 | Signed model/experiment receipts with synthetic-vs-observed evidence typing |
| W08 | Browser/device sessions, offline queue and per-surface audience binding |
| W09 | Algorithm agility, key IDs, revocation, replay protection, durable audit and trust roots |
| W10 | Qualification and specialist evidence carried as scoped signed records |
| W11 | Replication, fencing, regional authority and split-brain reconciliation |
| W12 | Ledger/payment/marketplace records use the same canonical envelope but separate domain-specific invariants and authority |

## 7. Conformance and acceptance suite

Before accepting a canonical profile, publish language-neutral fixtures and require each implementation to pass:
1. byte-identical canonical encoding and digest for all golden vectors;
2. malformed UTF-8, duplicate keys, alternate number forms, negative zero, large integers, nested structures and unknown fields;
3. signature verification, domain separation, wrong audience, wrong key ID, expired and not-yet-valid messages;
4. nonce replay, sequence rollback, key revocation and policy-epoch staleness;
5. major/minor schema compatibility, explicit migration and lossy downgrade rejection;
6. crash injection before/after enqueue, send, remote acceptance, effect, commit receipt, receipt verification and tombstone;
7. duplicate same-key/same-payload delivery and same-key/different-payload conflict;
8. process restart with pending encrypted outbox and pending receipt;
9. network partition, peer replacement, stale session and ambiguous timeout;
10. Python/Kotlin/Go/Rust interoperability against the same vectors and signed receipt fixtures.

A test pass is scoped to the tested build, profile, vectors and threat model; it does not prove all production compositions use the tested adapter.

## 8. New bounded closure gaps

- `GAP-W01-W09-CANONICAL-WIRE-ENCODING-AND-SIGNATURE-PREIMAGE`: no single accepted cross-language canonical encoding/signature profile with shared golden/negative vectors was established in the inspected source.
- `GAP-W02-W03-OFFLINE-OUTBOX-DURABILITY-AND-ATOMIC-TOMBSTONE`: inspected queue and sequence are process-local; crash-safe durable enqueue, receipt verification and tombstone transaction are not established.
- `GAP-W02-W03-W05-REMOTE-COMMIT-RECEIPT-AND-IDEMPOTENCY`: acknowledgement removes by execution ID and optional base-version comparison, without signed receipt binding exact payload/effect/final version/remote sequence.
- `GAP-W01-W08-SESSION-PRINCIPAL-DEVICE-AUDIENCE-AND-REVOCATION`: inspected gateway session binds a bootstrap-authenticated caller-provided client ID, but not a separately authenticated principal/device/audience or server-side revocation record.
- `GAP-W03-W09-JOURNAL-NAMESPACE-CHECKPOINT-AND-MIGRATION`: SQLite state journal has local sequence/digest checks; cross-journal namespace ownership, signed external checkpoint, migration ledger and key lifecycle remain unresolved.
- `GAP-W04-W05-W09-POLYGLOT-TOOL-AND-RESULT-RECEIPT-COMPATIBILITY`: in-process ToolSpec/ToolResult and runtime ActionEnvelope/Attestation require a shared typed wire contract and explicit adapters.

## 9. Decision status

This is an architecture proposal, not an accepted canonical encoding decision, protocol implementation, proof of remote settlement, or evidence that all ingress paths share the inspected gateway behavior. No tests were run. W01–W12 remain **PARTIAL**. The exact wire encoding, signature suite, storage backend and session trust profile remain OPEN until reviewed and accepted.
