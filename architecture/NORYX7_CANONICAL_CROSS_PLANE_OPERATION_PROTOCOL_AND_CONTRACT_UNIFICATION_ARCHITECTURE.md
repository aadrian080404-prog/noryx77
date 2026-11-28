# NORYX7 — Canonical cross-plane operation protocol and contract unification architecture

**Status:** ARCHITECTURE PROPOSAL — not implemented, not accepted as ADR, not operationally verified  
**Date:** 2026-11-28  
**Scope:** W01–W12; primary ownership W01/W02/W03/W04/W05/W06/W08/W09/W11  
**Change boundary:** architecture-only. No runtime/source/test/dependency/workflow/deployment or frozen-baseline changes.

## 1. Objective and invariant

Define one language-neutral protocol family through which every NORYX7 surface, agent, model adapter, tool, device, regional node, offline queue and external provider can express an intent, request work, delegate authority, attempt an action, report an effect, verify evidence and commit state.

**Invariant:** identity, intent, plan, action, authorization, dispatch, external effect, verification and state commit are distinct typed facts. No subsystem may infer one from another or translate a weaker receipt into a stronger one.

The protocol is a family of linked records, not one oversized universal object. Each record has a stable schema identity, version, canonical encoding profile, explicit issuer/audience/scope, lineage IDs, validity, integrity/authenticity material and a typed lifecycle state.

The protocol does not require every service to share one process, language, database or transport. It requires interoperable semantics and verifiable byte-level representations at trust boundaries.

## 2. Bounded source reconciliation

Snapshot reviewed: PR #212 branch HEAD a5d13222064dc3b74395eb69f555b982e678ca0c. Findings are bounded to the listed files and blobs.

| Source | Blob SHA | Bounded observation |
|---|---|---|
| core/contracts.py | a75491921288cbea6f1759ead99f97c83cfdc43d | TaskSpec, ActionSpec, VerificationResult and AgentResult use Python dataclasses, nested Any/Mapping and local well-formedness; no language-neutral wire schema, issuer/audience or signed receipt contract |
| noryx7_runtime/contracts.py | 9bb6632b214e8d9d3221c9ccf03ab6233209a184 | Separate Intent, ExecutionContext, PlanStep, ActionEnvelope and Attestation types; no declared wire-level mapping to core contracts |
| ecosystem/boundaries.py | a42ad0bdbde8aa05ee694b6aa9f5e2891538e718 | IntentEnvelope hashes payload and has front/operation/principal labels; make_intent defaults principal_id to front name when omitted, which is not authenticated identity |
| core/actions.py | 5e2fc212abea2873bb471b12e6fe6f5021664e97 | AuthorizationAuthority signs an action fingerprint and execution/principal/nonce/expiry with local HMAC JSON serialization; this is not a universal cross-language canonicalization/signature profile |
| core/identity.py | e6e8e5b03135251baca489643f86c7d81a755a08 | Ed25519 agent identity and attestation primitives with in-process IdentityRegistry; identity attestation is not a task, authorization, effect or commit receipt |
| core/tool_protocol.py | 1c529fbbf5352469be8ab6633edc48113da8a3bf | ToolSpec/ToolResult use local callable and free-form Any value/provenance; no wire schema, principal/audience, operation/attempt IDs or signed effect receipt |
| ecosystem/dispatch_contract.py | 87be053ccad3776d7eebf1cad280a4f52fec9ab6 | DispatchReceipt binds intent/front/execution/principal/accepted/reason/evidence digest; digest does not establish external effect |
| ecosystem/runtime_dispatch.py | 9f4f628c322aabb571fce64d54c3d6740cb142fd | Successful handler receipt hashes repr(type(value)); exception receipt records exception type; neither is a provider's independently verifiable effect receipt |
| core/state.py | f1dd791359038d799a63852ea850ce7f3d738148 | StateStore.commit requires caller boolean verification_valid=True, stage runtime_result, and principal/key fingerprint; boolean/stage are not themselves typed signed verifier receipts |
| core/offline.py | 6d0c5a76134fa679279406da1a514e628240debd | OfflineSyncQueue stores records and sequence in process memory; acknowledge removes by execution ID; reconnect accepts booleans; acknowledge_synced removes without a typed signed remote commit receipt bound to exact operation/effect |

The inspected source contains useful cryptographic, local validation and fail-closed primitives. The gap is semantic and cross-plane unification, not a claim that all existing primitives are insecure. External transport, gateway, provider or OS controls not present in these modules are not ruled out.

## 3. Protocol layers and record family

### 3.1 Common envelope header

Every wire record MUST carry protocol_family, schema_id, schema_version, canonicalization_profile, record_id, record_type, tenant/security_domain, issuer_id, issuer_key_id, audience, recipient_scope, creation and validity times with explicit time basis, correlation_id, causation_id, parent_record_ids, applicable operation/execution/attempt/step IDs, applicable policy/revocation/authority epochs, payload_digest, signature algorithm and signature (or explicit unsigned-local-only classification), data classification, retention policy, provenance refs and extension namespace.

Fields not applicable are omitted according to schema rules, not populated with misleading empty strings. Null, absent and empty are distinct where the schema permits them.

### 3.2 Typed records

1. **IntentRecord** — caller intent, authenticated principal reference, originating surface, payload reference/digest, requested outcome, constraints and consent basis. A front label or client_id is never an identity credential.
2. **WorkSpec** — canonical task objective, input/evidence refs, constraints, risk, verification obligations, deadline, resource budget and DAG dependencies.
3. **PlanRecord** — plan version, DAG step IDs, dependencies, selected agents, rationale, policy basis and plan digest. Plan proposal is not authorization.
4. **ActionRequest** — exact action type, target, canonical parameters, preconditions, desired effect, risk, idempotency key and operation lineage.
5. **DelegationGrant** — issuer, subject, audience, capability set, resource/target scope, constraints, validity, nonce, policy/revocation epoch, parent grant and attenuation chain.
6. **AuthorizationReceipt** — decision, policy version, exact ActionRequest digest, principal/device/workload identity, delegation chain, limits, issuer and expiry. It authorizes an attempt; it does not prove execution.
7. **DispatchAttempt** — destination worker/provider, lease/fencing token, attempt number, request digest, transport/session binding and outcome.
8. **EffectReceipt** — issued by the system that owns the external effect; binds operation/idempotency key, target, request digest, effect ID, provider transaction/reference, resulting version, effect state, timestamp basis and issuer signature. A local handler cannot impersonate the external effect owner.
9. **VerificationReceipt** — verifier identity/qualification, dependency profile, exact subject/evidence digests, checks performed, method/version, verdict, limitations, confidence semantics and signature.
10. **StateCommitReceipt** — authoritative aggregate, previous/new version, commit sequence, transaction ID, committed record digests, authority epoch and durable commit proof.
11. **ReconciliationRecord** — unknown/contradictory outcomes, evidence queried, provider response, retry/compensation decision, owner and final resolution.
12. **SyncReceipt** — remote acceptance or commit, explicitly distinct receipt type, exact offline envelope/operation digest, remote sequence/version, idempotency result and issuer proof.
13. **RevocationRecord** — target credential/grant/key/policy/qualification, issuer, effective time, monotonic revocation epoch, reason class and propagation evidence.
14. **AdmissionReceipt** — promotion of evidence/result into canonical memory or knowledge namespace, binding source lineage, verification, policy, authority and resulting version.

### 3.3 Typed receipt strength

The following states MUST NOT be conflated: request parsed; request accepted; dispatch attempted; worker acknowledged; handler returned; provider accepted; external effect committed; effect independently observed; result semantically verified; state durably committed; offline sync accepted; offline sync committed and reconciled.

A receipt proves only the assertion its issuer is authoritative to make. A broker receipt cannot prove a bank settlement; a runtime receipt cannot prove a physical actuator moved; a model verifier cannot prove a source record existed without an authenticated evidence path.

## 4. Canonical encoding and signature profile

Canonical encoding remains an OPEN decision. The architecture requires a versioned deterministic profile before selecting JSON, deterministic CBOR or another representation.

The profile MUST specify UTF-8 validity and Unicode normalization policy; duplicate-key rejection; map/object key ordering; integer bounds and exact decimal/float treatment; rejection or encoding of NaN/infinities; byte-string representation; absent/null/empty semantics; timestamp representation and precision; enum casing and unknown-field behavior; maximum record/nesting/collection/string sizes; canonical digest preimage and signature domain separation; algorithm identifiers, key IDs, rotation and revocation semantics; extension namespaces and downgrade prevention.

Do not sign language-specific object repr, default serializer output, unordered maps or display strings. Signature preimage MUST bind protocol family, schema ID/version, canonicalization profile, record type, issuer, audience, tenant/security domain and payload digest to prevent cross-protocol replay and type confusion.

A digest establishes content identity under the selected hash assumption; a signature establishes that a key signed specified bytes; neither establishes truth, authority scope, consent or successful external effect without corresponding issuer and policy validation.

## 5. Identity, principal and delegation semantics

Separate human/service principal, device/workload identity, agent identity, model/provider identity, tool identity, verifier identity and external effect owner. Each identity has an issuer, key binding, validity, audience, scope, status and revocation state.

- principal_id, client_id, front, agent_id and model name are identifiers, not proof of authentication by themselves.
- Agent keys attest the agent key holder, not the human who requested the work.
- Delegation is explicit, attenuable and bounded; child grants cannot expand parent capabilities.
- Bind every action grant to exact request digest, operation, execution, target, audience, principal, device/workload, expiry, nonce and policy/revocation epochs.
- One-shot nonce consumption needs durable replay protection across restarts and regions for globally meaningful grants.
- Local HMAC grants may remain valid within a declared trust domain, but cross-domain verification requires a documented issuer/key distribution profile; do not assume shared HMAC secrets across tenants.
- Revocation must be monotonic and freshness-bounded. If revocation status cannot be established for a high-risk action, fail closed or require an explicitly scoped degraded policy.

## 6. Operation identity and lifecycle

Use separate identifiers: intent_id (caller request), operation_id (durable business/physical/logical operation across retries), execution_id (one orchestration execution), step_id (one DAG node), attempt_id (one dispatch attempt), authorization_id (one grant/decision), effect_id (external effect owner identifier), verification_id (one verifier run), commit_id (one authoritative state commit), correlation_id and causation_id (tracing/lineage only).

An attempt is not an operation. Retrying creates a new attempt under the same operation and idempotency key unless the semantic operation is intentionally new. Correlation IDs do not authorize deduplication.

Proposed lifecycle:
PROPOSED → AUTHORIZED → READY → DISPATCHED → ACKNOWLEDGED → EFFECT_PENDING → EFFECT_COMMITTED | EFFECT_REJECTED | EFFECT_UNKNOWN → VERIFIED | VERIFICATION_FAILED → STATE_COMMITTED | RECONCILIATION_REQUIRED.

Terminal states are domain-specific. Cancellation after dispatch does not imply the external effect was cancelled. A timeout after dispatch yields EFFECT_UNKNOWN until reconciled, not FAILED and not safe-to-retry by default.

## 7. Idempotency, external effects and reconciliation

- Idempotency keys are scoped to issuer/tenant, operation type and target; they bind the canonical request digest.
- The effect-owning provider must define deduplication retention, query-by-key behavior and duplicate response semantics.
- Repeating the same key with a different payload is a conflict, not an update.
- At-least-once delivery is expected; exactly-once external execution is not assumed.
- After timeout/connection loss, query authoritative provider state or use a signed EffectReceipt; do not fail over to another provider blindly if the first may have acted.
- Separate provider acceptance receipt from settlement/commit receipt.
- Compensation is a new authorized operation with its own lineage, not deletion of the original effect.
- A state commit must reference the exact verification and effect receipts it admits.
- For providers without queryable/idempotent effects, define a human reconciliation path and block automatic retry of non-idempotent operations.

## 8. Offline and disconnected protocol

Offline local append, local verified result, remote acceptance and remote commit are distinct:
- offline operation uses a signed bounded snapshot, scoped capability and local monotonic sequence;
- encrypted outbox records are durable and crash-recoverable before the local operation is represented as pending sync;
- local result is explicitly LOCAL_COMMITTED_PENDING_RECONCILIATION, never globally committed;
- reconnect authenticates peer identity, audience, channel/session and current revocation/policy epoch cryptographically, not by caller booleans;
- remote acceptance does not delete the outbox item;
- a typed signed SyncReceipt/StateCommitReceipt must bind exact operation, attempt, payload digest, effect receipt, remote aggregate/version and remote sequence;
- deletion/tombstone of outbox item occurs atomically only after receipt verification and durable receipt persistence;
- duplicate replay returns the same committed result or explicit conflict;
- a partition or ambiguous outcome preserves the item for reconciliation; never silently drop or blindly replay.

## 9. Cross-language interoperability

Python, Kotlin, Go and Rust implementations MUST consume the same normative schemas and golden vectors. Language adapters map local types to/from wire records; local dataclasses/classes are not themselves the protocol.

Required conformance suites:
- canonical byte-for-byte encoding vectors, signatures and digests;
- malformed UTF-8, Unicode edge cases, duplicate keys, numeric boundaries and non-finite numbers;
- absent/null/empty, unknown fields, schema evolution and downgrade attacks;
- signature wrong-key, wrong-audience, wrong-tenant, expired, revoked and replay cases;
- request digest mutation and action-target substitution;
- idempotency duplicate, same key/different payload, timeout-after-effect and provider conflict;
- receipt type confusion (acceptance vs effect vs verification vs commit);
- offline crash/restart, outbox durability, replay, duplicate receipt and atomic tombstone;
- backward/forward compatibility and explicit unsupported-version rejection.

Golden vectors must be independently generated/reviewed, version-controlled and tested by all language implementations. No language team may redefine canonical semantics locally.

## 10. Versioning and evolution

Schema version is explicit per record type. Protocol family version and canonicalization profile version are separate. Compatibility policy must define additive optional fields, required-field changes, enum expansion, unknown critical extensions, deprecation windows and minimum supported versions.

Unknown noncritical extensions may be preserved byte-for-byte when safe; unknown critical extensions cause fail-closed rejection. Downgrade must never remove security-relevant fields silently. Migrations produce new records with provenance, not mutate signed historical bytes.

## 11. Privacy, security and resource constraints

Every record carries data classification, purpose, minimization, retention/deletion policy and allowed recipients. Signatures and immutable logs do not override privacy law or authorize indefinite retention. Sensitive payloads should be referenced through access-controlled content stores; metadata exposure must be assessed separately.

Enforce size/depth/rate limits, parser isolation, algorithm allowlists, key separation, tenant separation, replay cache capacity, lease expiry and bounded extension handling. Never deserialize executable code or trust remote type names as constructors. Provider secrets remain in dedicated secret custody, never in task/result envelopes.

## 12. Mapping current planes to the protocol

| Existing plane/type | Proposed mapping | Required restriction |
|---|---|---|
| core.TaskSpec | WorkSpec | Any/Mapping requires schema-bound payload references and validation |
| noryx7_runtime.Intent | IntentRecord | principal must be authenticated, not merely a string |
| PlanStep | PlanRecord node | plan proposal is not action authorization |
| ActionSpec / ActionEnvelope | ActionRequest | canonical payload, operation/attempt lineage and target scope |
| AuthorizationGrant | DelegationGrant + AuthorizationReceipt | local HMAC profile cannot be assumed portable across trust domains |
| AgentAttestation | identity attestation | not a verifier/effect/commit receipt |
| ToolSpec / ToolResult | Tool manifest + DispatchAttempt/typed result | handler return and free-form provenance are not external effect proof |
| DispatchReceipt | local dispatch receipt | accepted is not effect committed |
| VerificationResult / Attestation | VerificationReceipt | bind verifier, subject digest, method, evidence and independence profile |
| StateCommit | StateCommitReceipt | boolean verification marker must be replaced by exact receipt reference |
| OfflineSyncQueue / SyncEnvelope | durable offline outbox record | in-memory queue/sequence and ID-only ack do not satisfy remote commit protocol |
| MediaRef / evidence refs | content/evidence reference | digest does not replace custody, rights or source authenticity |

This is a mapping proposal; it does not change current source contracts or declare adapters implemented.

## 13. Cross-stream obligations W01–W12

- **W01:** principal/device/workload/agent/provider/verifier identity, issuer trust, audience, delegation attenuation and revocation.
- **W02:** operation/attempt lifecycle, DAG step IDs, dispatch receipts, cancellation and unknown-outcome reconciliation.
- **W03:** durable journal/outbox/inbox, canonical state commits, idempotency and recovery.
- **W04:** agent leases, delegated task scopes, worker identity, result and verifier receipt binding.
- **W05:** provider/tool manifests, secret custody, rate/cost limits, provider effect receipts and failure-domain identity.
- **W06:** evidence/verification receipts, claim lineage, independent verifier and typed proof obligations.
- **W07:** simulation/observation/effect types; simulator cannot issue real-world effect receipt.
- **W08:** device enrollment, browser/network lease, local/offline receipt and remote sync proof.
- **W09:** canonical encoding, signatures, key lifecycle, audit, replay defense and parser hardening.
- **W10:** specialist qualification credentials and jurisdiction-bound attestations.
- **W11:** durable distributed idempotency, lease/fencing, revocation freshness and cross-region commit authority.
- **W12:** payment/settlement/ledger/governance receipts issued by the actual authority/provider; no internal dispatch receipt represents cash settlement or legal mandate.

## 14. Failure behavior

| Condition | Required protocol result |
|---|---|
| Unknown schema/profile | Reject or quarantine; do not guess decode |
| Unauthenticated principal | Reject; do not use front/client label fallback |
| Expired/revoked grant | Deny before dispatch |
| Same idempotency key, changed request | Conflict and security event |
| Provider timeout after dispatch | EFFECT_UNKNOWN and reconciliation; no blind failover |
| Provider accepted but no settlement receipt | Pending effect; do not claim committed |
| Local verifier returns boolean only | Local check only; no cross-domain VerificationReceipt |
| Commit references missing/invalid receipt | Reject commit |
| Offline remote acceptance only | Keep outbox until verified commit receipt |
| Unknown critical extension | Fail closed |
| Key/policy epoch stale | Reject or enter explicitly bounded degraded mode |
| Simulator claims external effect | Type/issuer mismatch; reject |

## 15. Proposed gap additions

1. **GAP-W01-W09-CANONICAL-PROTOCOL-AND-SIGNATURE-PROFILE** — normative schema registry, deterministic bytes, signature preimage and domain separation.
2. **GAP-W01-W02-PRINCIPAL-DEVICE-AND-DELEGATION-BINDING** — authenticated principal/device/workload identity and attenuated delegation.
3. **GAP-W02-W03-UNIFIED-OPERATION-ATTEMPT-AND-RECEIPT-LINEAGE** — durable IDs and exact lineage across orchestration, actions, effects, verification and commits.
4. **GAP-W02-W05-TYPED-PROVIDER-EFFECT-AND-SETTLEMENT-RECEIPTS** — provider-issued effect proof distinct from local dispatch/acceptance.
5. **GAP-W03-W09-VERIFICATION-RECEIPT-BOUND-STATE-COMMIT** — replace caller booleans with exact signed/verified receipt references and atomic admission.
6. **GAP-W03-W08-DURABLE-OFFLINE-OUTBOX-AND-SIGNED-SYNC-COMMIT** — crash-safe queue, authenticated reconnect, remote receipt and atomic tombstone.
7. **GAP-W04-W05-TOOL-AND-AGENT-INTEROPERABILITY-CONTRACT** — portable manifests, capability scope, typed input/output and result provenance.
8. **GAP-W04-W06-VERIFIER-INDEPENDENCE-AND-ATTESTATION-BINDING** — verifier identity, qualification, dependency profile and exact subject binding.
9. **GAP-W09-W11-CROSS-REGION-REVOCATION-REPLAY-AND-IDEMPOTENCY** — durable replay protection, revocation freshness, authority epoch and partition behavior.
10. **GAP-W01-W02-W09-SCHEMA-VERSIONING-AND-DOWNGRADE-RESISTANCE** — schema negotiation, unknown critical fields and compatibility lifecycle.
11. **GAP-W05-W08-W09-PROVIDER-SECRET-AND-PAYLOAD-PRIVACY-BOUNDARY** — data minimization, purpose, retention, residency and secret separation.
12. **GAP-W01-W04-W05-W06-W07-W08-W10-W12-RECEIPT-ISSUER-AUTHORITY-MATRIX** — define which actor may issue each receipt type and what it proves.

These are proposed architecture closure requirements, not accepted ADRs or proof that all external systems lack such controls.

## 16. Decisions left OPEN

- Deterministic CBOR vs constrained canonical JSON or another profile.
- Schema registry format, governance and compatibility policy.
- Signature algorithms and key custody per trust domain.
- Principal/device/workload enrollment and issuer federation.
- Durable event/outbox/inbox and idempotency store technology.
- Receipt issuer authority and external provider integration contracts.
- Offline conflict and remote commit protocol.
- Verifier independence assurance levels and qualification registry.
- Payload reference/content-addressed storage, privacy, retention and deletion.
- Cross-region revocation freshness and partition policy.
- Transport selection and authenticated session/channel binding.
- Human escalation thresholds for unknown high-impact effects.

No specific broker, database, serialization library, consensus algorithm, transport or KMS/HSM vendor is selected by this proposal.

## 17. Acceptance criteria for later integration and validation

1. Every plane maps its local objects to normative versioned wire schemas without semantic loss.
2. Python/Kotlin/Go/Rust produce identical canonical bytes, digests and signature preimages for golden vectors.
3. Principal identity, audience, tenant, device/workload and delegation are cryptographically bound.
4. Authorization, dispatch, effect, verification and commit receipts cannot be substituted for one another.
5. A positive local dispatch cannot be reported as external effect committed.
6. A state commit cannot accept a bare boolean as proof; it references an admissible verifier receipt.
7. All attempts share one durable operation/idempotency lineage; ambiguous effects are reconciled before retry.
8. Offline queue survives process crash/restart and is removed only after a verified remote commit receipt is durably recorded.
9. Revocation, expiry, replay and downgrade tests pass across regions and languages.
10. Privacy classification, purpose, retention and recipient policy are enforced at every boundary.
11. Every receipt type has a documented authoritative issuer and explicit proof scope.
12. W01–W12 end-to-end conformance tests prove no cross-plane contract drift.

**Closure statement:** This document defines a candidate canonical protocol family and source-bounded reconciliation. It does not choose the final encoding, accept an ADR, implement adapters, or claim interoperability. W01–W12 remain PARTIAL pending architecture consolidation, decision approval, implementation, integration and evidence-backed verification.
