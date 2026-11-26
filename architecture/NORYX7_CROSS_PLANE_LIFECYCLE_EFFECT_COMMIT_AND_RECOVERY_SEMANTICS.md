# NORYX7 — Cross-Plane Lifecycle, Commit, Receipt and Recovery Semantics

**Audit date:** 2026-11-26  
**Source snapshot:** `12a439ffd27692570b01d75e96f5ab33e9d3ea76`  
**Scope:** lifecycle/state/dispatch/attestation/authorization/evaluation semantics across W01–W12. Architecture-only; no executable source, tests, dependencies, workflows or deployment configuration changed.  
**Disposition:** proposed canonical semantics for review, not an accepted ADR or implementation. W01–W12 remain PARTIAL.

## 1. Purpose and evidence boundary

The previous call-site audit mapped where components are constructed and consumed. This pass maps what their records mean over time: authorization grant, dispatch attempt, observed output, verification, attestation, commit, receipt, terminal execution state and recovery. These are not interchangeable events.

Source inspection is bounded to the file/blob revisions listed in §10. No test execution or external production telemetry is claimed. The architecture recommendations below are normative proposals, not claims that the repository already implements them.

## 2. Existing lifecycle models are deliberately different

### 2.1 RuntimeEngine execution lifecycle

`noryx7_runtime/contracts.py` defines `ExecutionStatus`:
`CREATED → RUNNING → {SUCCEEDED, REJECTED, FAILED, CANCELLED}`.
`noryx7_runtime/lifecycle.py` enforces terminal-state semantics in an immutable `ExecutionLifecycle`. This is a sound local state-machine boundary, but it is in-memory and does not itself persist every transition or prove the real-world side-effect state.

### 2.2 HYPERSYNTH state lifecycle

`core/state.py` uses `NORYXState.status` as a string, initially `initialized`; `StateStore.commit()` snapshots it and changes the stored copy to `committed`. It accepts caller-provided `verification_valid=True`, `verification_stage="runtime_result"`, principal ID and key fingerprint, then optionally writes through `core.state_journal.StateJournal`. The journal is durable SQLite WAL/FULL with replay and digest checks, but the commit API's boolean and stage string are assertions supplied by its caller, not a proof object independently verified by the journal.

### 2.3 Dispatch receipt lifecycle

`ecosystem/dispatch_contract.py` defines a `DispatchReceipt` with intent/source/target/execution/principal, accepted flag, reason and evidence digest. `ecosystem/runtime_dispatch.dispatch()` authorizes a principal and executes a handler, but the success receipt hashes `repr(type(value))`, not the returned value, downstream state or independently observed effect. A handler exception produces an accepted=False receipt. Thus this is an authenticated-boundary/handler-outcome receipt only to the extent of the surrounding trust contract; it is not a proof that an external side effect happened or did not happen.

### 2.4 Agent result lifecycle

`core/coordination.py` creates one execution ID, selects up to `max_agents` plan steps, dispatches sequentially, and checks returned AgentResult identity, task/execution IDs, status and verifier markers. Its consensus check requires all outputs to be equal. It does not establish semantic independence of the agents, independence of their verifier, or that the results were generated from distinct evidence sources. “Consensus” here means structural agreement under the current verifier contract, not independent corroboration.

### 2.5 Authorization grant lifecycle

`core/actions.py` issues HMAC-signed, one-shot grants bound to action fingerprint, execution, optional principal key fingerprint, nonce and expiry. `consume_and_execute()` serializes grant consumption against identity revocation under locks, consumes before invoking the executor, and deliberately does not restore a grant after executor failure. This is correct fail-closed authorization behavior, but it creates a distinct operational fact: **authorization consumed** does not mean **dispatch succeeded**, and neither means **effect committed**. Those outcomes need separate durable records.

## 3. Dispatch, effect and commit are different facts

The current source paths expose several boundaries:

| Event | Meaning | Must not be interpreted as |
|---|---|---|
| AuthorizationDecision | Policy permits or denies a specific request | Action was dispatched |
| AuthorizationGrantConsumed | One-shot capability cannot be reused | Remote operation completed |
| DispatchAttempt | A handler/provider was invoked with a specific request | External side effect occurred |
| HandlerReturn | Local callable returned a value | Remote state changed as intended |
| EffectObserved | An authoritative observer reports a concrete effect | State was durably committed |
| VerificationResult | A named verifier accepted a specific artifact/result | Independent semantic truth unless verifier/evidence are qualified |
| Attestation | A signer binds declared fields to a key | The declared effect is true absent trusted observation |
| StateCommit | A specific state snapshot is durably committed | External side effect and local state were atomic |
| DispatchReceipt | A dispatch boundary reports accepted/rejected with evidence digest | Settlement/finalization proof |
| RuntimeTerminalStatus | A local execution reached terminal lifecycle state | Every external system has reconciled |

**Required invariant:** every operation must retain a stable `operation_id`, with distinct `attempt_id`, `authorization_id`, `effect_id`, `verification_id`, `attestation_id`, and `commit_id`. IDs must not be overloaded or regenerated across retry boundaries.

## 4. RuntimeEngine reservation and partial-commit semantics

The inspected `RuntimeEngine.execute()`:
1. creates an execution lifecycle and schedules steps;
2. performs high-risk authorization;
3. reserves a step in `noryx7_runtime.state.StateJournal` before dispatch when that journal is supplied;
4. invokes the adapter/executor;
5. calls a supplied verifier;
6. creates and optionally signs an Attestation;
7. appends the attestation to the runtime journal;
8. invokes an optional external committer;
9. restores the reservation if the external committer fails after journal append, failing closed against redispatch.

Important distinctions:
- The reservation is an anti-duplicate dispatch barrier, not proof of effect completion.
- The attestation binds action/output digests and declared verification outcome; its trust depends on signer identity and the truth/independence of the verifier.
- The in-memory runtime journal and the external committer are not one atomic transaction.
- The code preserves a reservation when dispatch/commit has crossed the side-effect boundary, which is conservative for duplicate prevention; it does not, by itself, reconcile whether the side effect happened.
- A crash between external effect and durable local evidence can leave an unknown outcome. A retry must not blindly repeat a non-idempotent operation.

The canonical state machine therefore needs an explicit `EFFECT_UNKNOWN` / `RECONCILIATION_REQUIRED` state. It must never collapse timeout, process crash or missing receipt into “not executed”.

## 5. Canonical operation state machine — proposed

The following is a normative proposal for the cross-plane contract, not a replacement of each existing internal state machine:

```text
CREATED
  ├─> DENIED                         (authorization refused; no dispatch)
  └─> AUTHORIZED
        └─> DISPATCH_RESERVED        (idempotency/lease reserved)
              └─> DISPATCH_ATTEMPTED
                    ├─> EFFECT_UNKNOWN          (timeout/crash/ambiguous return)
                    ├─> EFFECT_REJECTED         (authoritative no-effect proof)
                    └─> EFFECT_OBSERVED
                          └─> VERIFICATION_PENDING
                                ├─> VERIFICATION_REJECTED
                                └─> VERIFIED
                                      └─> COMMIT_PENDING
                                            ├─> COMMIT_FAILED
                                            └─> COMMITTED
                                                  └─> RECONCILED
```

Rules:
- `DENIED` is terminal for that authorization attempt, not necessarily for the user's higher-level intent.
- `EFFECT_REJECTED` requires authoritative evidence of no effect; a handler exception is insufficient.
- `EFFECT_UNKNOWN` blocks automatic redispatch until reconciliation or an idempotent replay contract explicitly permits retry.
- `VERIFIED` is scoped to exact artifact digest, verifier identity/version, evidence set and policy epoch.
- `COMMITTED` means the authoritative state store accepted a specific commit ID and sequence; it does not silently imply payment settlement or external transaction completion.
- `RECONCILED` requires every external effect and internal commit for the operation to be accounted for.
- Terminal execution status remains separate from operation/effect state. One execution can contain multiple operations with different outcomes.

## 6. Canonical records and minimum required fields — proposed

### 6.1 OperationEnvelope
`operation_id`, `intent_id`, `execution_id`, `tenant_id`, `principal_assertion_id`, `action_digest`, `target`, `idempotency_key`, `policy_epoch`, `created_at`, `deadline`, `schema_id/version`, `provenance`.

### 6.2 AuthorizationReceipt
`authorization_id`, `operation_id`, `decision`, `policy_id/version`, `principal_assertion_id`, `capability_scope`, `audience`, `expires_at`, `nonce_digest`, `issuer_key_id`, `signature`.

### 6.3 DispatchAttempt
`attempt_id`, `operation_id`, `adapter_id/version`, `destination`, `request_digest`, `idempotency_key`, `started_at`, `deadline`, `transport_outcome`, `response_digest`, `retry_of`, `trace_id`.

### 6.4 EffectReceipt
`effect_id`, `operation_id`, `attempt_id`, `effect_state` (observed/rejected/unknown), `target_system`, `target_transaction_id`, `observed_at`, `observer_id`, `evidence_digest`, `evidence_location`, `signature`. Unknown must be a first-class value, not an exception string.

### 6.5 VerificationReceipt
`verification_id`, `operation_id`, `artifact_digest`, `evidence_ids`, `verifier_identity/version`, `verification_profile`, `policy_epoch`, `decision`, `limitations`, `signature`.

### 6.6 StateCommitReceipt
`commit_id`, `operation_id`, `state_store_id`, `sequence`, `previous_commit_digest`, `state_digest`, `verification_receipt_id`, `principal_assertion_id`, `committed_at`, `signature`.

### 6.7 ReconciliationRecord
`reconciliation_id`, `operation_id`, all attempt/effect/verification/commit IDs, `final_disposition`, `unresolved_items`, `reconciler_identity`, `evidence_digest`, `reconciled_at`, `signature`.

## 7. Retry, timeout, crash and compensation rules — proposed

| Failure boundary | Safe default | Required next action |
|---|---|---|
| Before authorization | No dispatch | Re-authorize if policy/identity changes |
| Authorization denied | Do not dispatch | Return denial with policy evidence |
| Grant consumed, executor not entered | Do not reuse grant | New authorization after inspecting dispatch attempt |
| Dispatch entered, no authoritative response | Mark EFFECT_UNKNOWN | Query target by idempotency/transaction key |
| Target confirms no effect | Mark EFFECT_REJECTED | Retry only under new attempt and valid authorization |
| Target confirms effect, local commit absent | Keep reservation | Reconstruct/commit from signed EffectReceipt |
| Verification fails after effect | Do not erase effect | Quarantine result; compensate only with separate authorized operation |
| Local commit succeeds, external finalization fails | Do not report reconciled | Retry finalization idempotently; preserve commit |
| Crash during multi-system operation | Mark unresolved | Recovery worker loads durable outbox/inbox and reconciles each participant |
| Compensation requested | New operation with parent link | Separate approval, effect receipt and audit chain |

Never use a blind “rollback” label for a real-world effect that cannot be atomically reversed. Compensation is a new authorized operation with its own receipt and audit trail.

## 8. Concurrent W01–W12 closure consequences

| Workstream | Lifecycle/receipt requirement |
|---|---|
| W01 Identity & Trust | Bind every authorization and receipt to PrincipalAssertion, key, audience, scope, epoch and revocation freshness |
| W02 Runtime | One operation identity propagated through scheduler, execution plane, adapters, provider calls and result admission |
| W03 Memory & State | Distinguish reservation, append, durable commit, replay recovery and reconciliation; identify authoritative journal per runtime |
| W04 Agent Fabric | AgentResult includes operation/attempt/evidence lineage; consensus must declare independence assumptions and verifier provenance |
| W05 Routing & Providers | Idempotency key, attempt IDs, unknown-effect state and retry owner mandatory across every provider path |
| W06 NEXUS / FRL | VerificationReceipt binds exact claims/evidence/verifier profile; no caller boolean promoted to proof |
| W07 MIRROR WORLD | Simulation result cannot be an EffectReceipt; Reality Bridge requires a distinct approval and observed-effect record |
| W08 Surfaces | Surface request IDs map to stable operation IDs; client disconnect/timeout does not imply cancellation of external effect |
| W09 Security | Authorization consumption, audit event, signed attestation and incident record have independent lifecycles and retention |
| W10 Specialist Domains | Specialist result includes qualification scope, evidence provenance and domain-specific verifier |
| W11 Global Operations | Leases/reservations have owner, TTL, fencing token, renewal/release and recovery semantics |
| W12 Economy & Impact | Payment, escrow, settlement, refund/chargeback, ledger commit and impact evidence are separate state machines |

## 9. New gaps and decision requirements

- `GAP-OPERATION-EFFECT-STATE-MACHINE-AND-UNKNOWN-OUTCOME`: define durable operation/effect state independently of execution terminal status.
- `GAP-AUTHORIZATION-CONSUMPTION-TO-DISPATCH-RECEIPT-LINKAGE`: persist consumed grants and dispatch attempts with one operation identity; executor failure must not be misread as no effect.
- `GAP-CROSS-STORE-COMMIT-AND-RECONCILIATION`: define recovery across runtime journal, HYPERSYNTH StateStore/SQLite journal, external committer and target-system effect.
- `GAP-RECEIPT-EVIDENCE-SEMANTICS`: replace type-only evidence digests and caller-asserted verification booleans with typed, authenticated, observer-bound receipts.
- `GAP-AGENT-CONSENSUS-INDEPENDENCE-AND-PROVENANCE`: define what counts as independent agents, sources, verifiers and evidence; equality of output is not independent corroboration.
- `GAP-RETRY-IDEMPOTENCY-AND-COMPENSATION-OWNERSHIP`: specify retry authority, deduplication retention, target query and separately authorized compensation.

Decision owners must decide whether a shared cross-plane operation protocol is authoritative and how legacy state machines map to it. No existing ADR is accepted by this document. No source code is changed, no tests are run, no PR is merged and no deployment is claimed.

## 10. Source traceability

| Source path | Blob SHA | Relevance |
|---|---|---|
| `noryx7_runtime/contracts.py` | `9bb6632b214e8d9d3221c9ccf03ab6233209a184` | ExecutionStatus, Intent, ActionEnvelope, Attestation |
| `noryx7_runtime/lifecycle.py` | `71d1079f0cf1aa9cd70a097ad2a9e6365dce38b5` | Allowed execution terminal transitions |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` | Reservation → dispatch → verify → attest → journal → committer |
| `noryx7_runtime/state.py` | `444aba1fb92a4bb70ee2ee31b23d3946680bb630` | Step reservation, attestation journal, restore reservation |
| `noryx7_runtime/attestation.py` | `b417bdb09f5ad920f7b6cf96910aea5c6447ac2a` | Ed25519 and identity/chain verification primitives |
| `core/actions.py` | `5e2fc212abea2873bb471b12e6fe6f5021664e97` | One-shot grant consumption and consume-before-execute |
| `core/contracts.py` | `a75491921288cbea6f1759ead99f97c83cfdc43d` | Task/action/result structures |
| `core/coordination.py` | `c5743872a5b50765db04e4a42739e9ad238ad983` | Sequential agent execution, result checks and equality consensus |
| `core/state.py` | `f1dd791359038d799a63852ea850ce7f3d738148` | StateStore commit API and caller-supplied verification arguments |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite WAL/FULL state commit journal |
| `ecosystem/dispatch_contract.py` | `87be053ccad3776d7eebf1cad280a4f52fec9ab6` | DispatchReceipt and evidence digest |
| `ecosystem/runtime_dispatch.py` | `9f4f628c322aabb571fce64d54c3d6740cb142fd` | Principal authorization and handler dispatch |
| `core/evaluation.py` | `df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e` | Caller-recorded EvaluationResult matrix |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` | Deterministic case/holdout generation and externally supplied result recording |
| `core/supply_chain.py` | `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5` | Signed artifact manifest and artifact-byte digest verification |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` | Local capacity selection/accounting and recovery helpers |

