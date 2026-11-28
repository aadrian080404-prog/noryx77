# NORYX7 — Schema Compatibility, Contract Collisions and Interoperability Audit

**Audit date:** 2026-11-26  
**Audited source-tree commit:** `f0b43470d6855567f8c4034bb50b68db10453565`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Scope:** architecture-only source reconciliation across W01–W12.  
**Disposition:** findings and proposed mappings only; no schema is accepted, no runtime code is changed, and no integration or test campaign is authorized.

## 1. Executive finding

The repository contains multiple locally valid contract families that describe adjacent concepts but are not interchangeable. The most consequential collisions are:

1. multiple unrelated types named `Attestation`, with different trust subjects and cryptographic semantics;
2. overlapping task/action/result envelopes with different identity, execution, status and verification fields;
3. tool, dispatch, verification and execution receipts whose success fields and evidence digests prove different things;
4. several state vocabularies that cannot safely be collapsed into one global enum;
5. offline and multimodal records that carry digests/locators but do not by themselves establish custody, authenticity, durable acknowledgement or consent;
6. a synthetic default principal in the cross-front intent helper that is not an enrolled identity assertion.

This is not a finding that these primitives are individually defective. It is an interoperability and ownership problem: a consumer can receive a structurally plausible object whose meaning is narrower than the consumer assumes.

## 2. Source snapshot and evidence method

The branch pointer was read immediately before this audit and resolved to `f0b43470d6855567f8c4034bb50b68db10453565`. The following exact source blobs were inspected:

| Source | Blob SHA | Bounded role |
|---|---|---|
| `core/contracts.py` | `a75491921288cbea6f1759ead99f97c83cfdc43d` | TaskSpec, ActionSpec, VerificationResult, AgentResult |
| `noryx7_runtime/contracts.py` | `9bb6632b214e8d9d3221c9ccf03ab6233209a184` | Intent, ExecutionContext, PlanStep, ActionEnvelope, runtime Attestation, ExecutionStatus |
| `core/identity.py` | `e6e8e5b03135251baca489643f86c7d81a755a08` | Ed25519 AgentIdentity and AgentAttestation |
| `core/attestation.py` | `48a5145b33c73c9e8d3b1f0051050dd97f89786f` | RuntimeIdentity external-attestation abstraction |
| `noryx7_runtime/attestation.py` | `b417bdb09f5ad920f7b6cf96910aea5c6447ac2a` | Runtime action attestation signer/verifier and chain digest |
| `core/tool_protocol.py` | `1c529fbbf5352469be8ab6633edc48113da8a3bf` | ToolSpec and ToolResult |
| `ecosystem/boundaries.py` | `a42ad0bdbde8aa05ee694b6aa9f5e2891538e718` | Front and IntentEnvelope |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` | DispatchReceipt |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` | Structural verification semantics |
| `core/offline.py` | `6d0c5a76134fa679279406da1a514e628240debd` | OfflineSnapshot, OfflineExecution, SyncEnvelope and queue |
| `core/agent_skills.py` | `281d294ee0142a8dd33db5d61f634f95943db231` | Declarative skill registration |
| `core/agent_fabric.py` | `3704dd7bf66815274cc319c9583c45ae575f3d36` | Principal-bound native agent dispatch |

The inspection was source-level and bounded to these blobs and the recursive repository tree at the audited commit. It is not a runtime trace, migration test, full caller inventory or claim that external adapters do not exist.

## 3. Collision register

### C01 — Attestation type-name collision

Three different meanings are exposed under the same or adjacent terminology:

- `core.identity.AgentAttestation`: Ed25519 statement signed by an agent identity; statement bytes are generic and identity registry trust is optional at verification call time.
- `noryx7_runtime.contracts.Attestation`: runtime action/result record bound to execution, principal, step, agent, key fingerprint, action/output digests, verified flag, previous digest and runtime/provenance fields. It becomes cryptographically signed through the separate `noryx7_runtime.attestation` module.
- `core.attestation.Attestation`: runtime measurement claim (runtime_id, measurement, issued/expiry, nonce) consumed by an external AttestationVerifier for runtime identity binding.

These records answer different questions: “which agent signed this statement?”, “what did this execution step claim?”, and “what runtime measurement was externally attested?”. They must not share a generic decoder, trust store, acceptance flag or interchangeability assumption. The shared word “attestation” is not a shared schema.

**Required design decision:** canonical typed names and explicit purpose/domain separation, e.g. AgentStatementAttestation, ExecutionStepAttestation and RuntimeMeasurementAttestation, with separate issuer trust roots, audience, validity, revocation and evidence scope. A migration alias may be retained only at a versioned adapter boundary.

### C02 — Task/action/plan envelope overlap

- `core.contracts.TaskSpec` carries task_id, task_type, objective, input, constraints, verification requirements, risk class and optional execution_id.
- `core.contracts.ActionSpec` carries action_id, action_type, target, parameters, risk class, authorization requirement and execution_id.
- `noryx7_runtime.contracts.Intent` carries text, principal_id and generated intent_id.
- `noryx7_runtime.contracts.ExecutionContext` carries execution_id, principal_id, deadline, max_actions and local ExecutionStatus.
- `noryx7_runtime.contracts.PlanStep` carries step_id, action_type, target, parameters and dependencies.
- `noryx7_runtime.contracts.ActionEnvelope` binds execution_id, principal_id, step_id, action, parameters and nonce.

The overlap is intentional at different lifecycle stages, but there is no single type-level parent/child relationship demonstrated by these definitions. In particular, TaskSpec and Intent are not equivalent; PlanStep is not an authorized ActionEnvelope; ActionSpec's boolean `requires_authorization` is not an AuthorizationReceipt; and execution_id alone does not prove common issuer, tenant, policy epoch or parent operation.

**Required design decision:** define explicit translation edges and preserve stable operation_id → intent_id/task_id → execution_id → step_id → attempt_id lineage. Each adapter must reject missing or conflicting principal, audience, policy epoch and action fingerprint instead of filling them with defaults.

### C03 — Result, tool and dispatch receipt non-equivalence

- `core.contracts.VerificationResult` is a local structure with `valid`, `stage`, `reason` and details. It has no verifier identity, signature, artifact digest or evidence custody reference.
- `core.contracts.AgentResult` carries agent_id, task_id, free-form status, output, optional VerificationResult and execution_id.
- `core.tool_protocol.ToolResult` carries tool, success, value/error and a provenance string such as tool@version. It is not signed and does not independently establish an external effect.
- `ecosystem.dispatch_contract.DispatchReceipt` carries intent/source/target/execution/principal, accepted, reason and a digest of caller-provided evidence bytes. The digest establishes byte integrity relative to the supplied evidence, not evidence truth or effect completion.
- `noryx7_runtime.contracts.Attestation` carries action/output digests and a verified boolean within a separately signed runtime record.

The words `valid`, `verified`, `accepted`, `success` and `completed` are not equivalent. A ToolResult success may mean the handler returned; a DispatchReceipt accepted may mean dispatch was accepted; a VerificationResult valid may mean a structural check passed; an execution attestation may bind a signed claim. None alone proves that an external target applied exactly one intended effect.

**Required design decision:** type distinct receipts by lifecycle stage and include observer identity, subject/effect identity, exact request/response digests, evidence references, signature/trust profile, observation time, idempotency key and uncertainty. Success promotion must require an explicit policy mapping between receipt types.

### C04 — Status and terminal-state vocabulary collision

Observed vocabularies include:

- `ExecutionStatus`: created, running, succeeded, rejected, failed, cancelled.
- `VerificationEngine`: task/state status values initialized, processing, completed; result verdict unknown, success, failure.
- `AgentResult.status`: arbitrary non-empty string, with one verifier path requiring exactly completed.
- `OfflineState`: online, disconnected, offline_ready, offline_executing, sync_pending, reconnecting, syncing, conflict, recovery.
- state-store status such as initialized/committed and lifecycle states in other local journals.

These vocabularies describe different aggregates. Mapping `failed` to “no effect”, `cancelled` to “nothing happened”, `completed` to “verified”, or `sync_pending` to execution failure would be unsafe. Offline synchronization, evidence admission, execution and external effect require separate state machines.

**Required design decision:** maintain aggregate-specific enums and define only explicit, loss-aware mapping tables. Include UNKNOWN/INDETERMINATE where an external effect cannot be established. Terminal execution status must never overwrite effect certainty or settlement status.

### C05 — Principal and identity assertion collision

`ecosystem.boundaries.make_intent` accepts an optional principal_id and defaults it to `front.value` when omitted. This is a deterministic front label, not proof of a user, device, tenant or enrolled service principal. By contrast, `noryx7_runtime.contracts.Intent` requires a non-empty principal_id; `AgentFabric.dispatch` receives principal_id from its caller and binds it into request context; `gateway.auth.SessionAuthority` signs a caller-supplied client_id after bootstrap authentication, while the inspected RuntimeAdapter passes that label into task constraints.

These values may all be strings but have different issuers and assurance levels. A front name/client label must not be silently upgraded to PrincipalAssertion or authorization subject.

**Required design decision:** prohibit synthetic principal fallback for privileged or attributable operations; represent anonymous/front-origin context separately from authenticated principal; bind session audience, device/client enrollment, tenant, policy epoch, expiry and revocation state through an issuer-verifiable assertion.

### C06 — Media digest and offline sync record do not establish custody

`MediaRef` records modality, content_type, SHA-256 digest and locator. Its digest binds bytes supplied at construction, but the record does not itself authenticate locator ownership, capture provenance, rights/consent, encryption-at-rest, retention or transformations. `OfflineSnapshot` checks a canonical integrity digest and delegates authenticity to an injected authenticator; `SyncEnvelope` includes ciphertext, ciphertext digest and in-process sequence; `OfflineSyncQueue` is an in-memory outbox whose acknowledgement removes the record.

These are useful local integrity and queue primitives, not a shared durable MediaCustodyRecord or end-to-end sync acknowledgement. A digest does not prove who captured or supplied media, and queue acknowledgement does not prove remote durable commit unless the remote acknowledgement is authenticated and bound to the exact record and sequence.

**Required design decision:** distinguish ContentDigest, CustodyRecord, Consent/rights assertion, SnapshotAuthenticityReceipt, SyncDeliveryAttempt and RemoteCommitReceipt. Specify durable outbox/inbox, replay window, authenticated acknowledgement, deletion/retention and reconciliation.

### C07 — Skill, capability and authority semantics

`AgentSkill` and `ToolSpec.capabilities` describe registered skills/tool capability labels. `AgentFabric` separately requires trusted identity and an authorization callback for principal dispatch; `ToolRegistry.invoke` requires an authorization callback to return exactly True. Registration and descriptive capability labels are not CapabilityDecision or DelegationGrant. `ActionSpec.requires_authorization` is declarative and does not carry the grant itself.

**Required design decision:** normalize capability identifiers and versions, but keep qualification, registration, delegation and per-operation authorization as separate signed/issuer-owned records. No skill/tool registry may be treated as an authority source by itself.

## 4. Cross-workstream impact map

| Workstream | Collision families | Required closure |
|---|---|---|
| W01 Identity/trust/authorization | C01, C03, C05, C07 | issuer-specific identity and attestation profiles; no synthetic principal promotion |
| W02 Runtime/orchestration | C02, C03, C04 | explicit intent/task/operation/execution/step mapping and aggregate state separation |
| W03 Memory/state/recovery | C01, C03, C04, C06 | durable custody and receipt references; replay/recovery state mappings |
| W04 Agent fabric | C01, C02, C03, C07 | agent identity, skill, delegation, result and attestation separation |
| W05 Routing/providers/resources | C02, C03, C04, C07 | provider/tool/dispatch/effect receipt semantics and idempotency |
| W06 NEXUS/FRL/evidence/reasoning/evaluation | C01, C03, C06 | evidence provenance, verifier identity, typed claims and custody |
| W07 MIRROR WORLD/simulation/Reality Bridge | C03, C04, C06 | simulation evidence cannot be promoted to real effect receipt |
| W08 Surfaces/devices/browser/offline | C02, C04, C05, C06 | surface identity, offline state and authenticated sync receipt |
| W09 Security/crypto/audit/release | C01, C03, C05, C06 | domain-separated signing profiles, trust roots, revocation and audit |
| W10 Specialist/domain intelligence | C01, C03, C07 | qualification/credential/claim authority remain distinct |
| W11 Global distribution/operations | C01, C03, C04, C06 | fleet/runtime attestation and durable delivery/commit semantics |
| W12 Economy/governance/impact | C03, C04, C06, C07 | provider success is not settlement; impact evidence requires custody and independent measurement |

## 5. Proposed canonical compatibility rules (not accepted ADR)

1. **No same-name type equivalence.** Canonical identity is (schema_id, schema_version, semantic_profile), not Python class name.
2. **No implicit success promotion.** A lower-stage receipt cannot be consumed as a higher-stage receipt without a named, testable policy adapter.
3. **No identity synthesis.** A surface/front/client label is not a principal assertion.
4. **No global status enum.** Keep operation, execution, effect, verification, offline sync, release, settlement and impact state distinct.
5. **No digest-as-truth inference.** A digest proves byte correspondence, not authenticity, source authority, semantic correctness or effect.
6. **No registry-as-authority inference.** Registration, skill membership and provider capability do not grant a principal permission.
7. **Version every cross-plane adapter.** Adapters declare accepted source schema versions, emitted target version, lossiness, rejected fields, issuer/audience checks and deprecation window.
8. **Invalidate dependent evidence.** A source blob or schema mapping change invalidates only the evidence cards and workstream claims that depend on it, with transitive dependency recorded.

## 6. Required closure artifacts before integration

- A machine-readable schema registry with canonical IDs, owners, versions and compatibility policy.
- An explicit producer/consumer/adapter matrix for every actual constructor, route, registry and call site.
- A typed receipt promotion policy covering accepted, dispatched, observed, verified, committed, reconciled and unknown outcomes.
- Separate trust profiles for agent statement, runtime execution and runtime measurement attestations.
- Principal assertion and anonymous/front-origin distinction with issuer, audience, tenant, device/client, expiry, revocation and policy epoch.
- Aggregate-specific state mapping tables and unknown-outcome handling.
- Media custody, consent/rights, offline durable outbox/inbox and authenticated remote commit contracts.
- Migration/deprecation and rollback plan, then integration tests after architecture completion.

## 7. Limits and disposition

This audit does not assert that every proposed record is absent elsewhere, that any observed collision is exploitable, or that the current implementation is globally insecure. It identifies semantic non-equivalence in the inspected contract definitions and the need for explicit adapters and owners. No source code, tests, workflows, dependencies, deployment configuration or frozen baseline were modified.

**W01–W12 remain PARTIAL.** No ADR is accepted. No integration, comprehensive verification or architecture freeze is claimed.
