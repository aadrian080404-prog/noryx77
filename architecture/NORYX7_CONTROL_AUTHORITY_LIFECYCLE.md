# NORYX7 — Control Authority, Runtime and State Lifecycle Architecture

**Status:** architecture proposal for cross-plane reconciliation; no implementation or verification is claimed  
**Scope:** canonical identity, policy, capability, ActionGate, agents, runtime, state commit, audit and recovery boundaries  
**Source anchors:** `core/identity.py`, `core/policy.py`, `core/actions.py`, `core/agent_fabric.py`, `noryx7_runtime/capabilities.py`, `noryx7_runtime/engine.py`, `noryx7_runtime/state.py`, `core/recovery.py`.

## 1. Design decision

NORYX7 uses one logical control-authority chain across all surfaces and execution locations:

`PRINCIPAL IDENTITY → AUTHENTICATION → REQUEST CONTEXT → POLICY DECISION → CAPABILITY GRANT → ACTION ENVELOPE → RUNTIME ADMISSION → ADAPTER EXECUTION → RESULT ATTESTATION → INDEPENDENT RESULT VERIFICATION → STATE COMMIT`

This is a logical authority model, not a claim that every current code path already uses one shared implementation. Existing modules/facades must be mapped to this model through later compatibility adapters and ownership decisions.

No model, agent, planner, route selector, semantic artifact, simulation result, provider or surface can mint or widen authority.

## 2. Authority ownership

| Concern | Canonical owner | May propose | Must not be delegated to |
|---|---|---|---|
| Principal identity | Identity registry / trusted identity provider | User/device/agent identity claim | LLM, planner, memory, Browser page |
| Authentication | Authenticator and key/channel boundary | Credential or attestation evidence | Model or application prompt |
| Policy | Policy decision point and versioned policy store | Action request/context | Agent, provider, tool adapter |
| Capability issuance | Capability broker | Required scope and target | Router, plan, skill manifest |
| Action admission | ActionGate/runtime control plane | Exact action envelope | Model, Browser, terminal shell |
| Execution | Registered adapter in isolated runtime | Execution result | Unregistered process or arbitrary tool |
| Result verification | Independent verifier(s) | Verification request | Same untrusted producer as sole verifier |
| State commit | Authoritative state/commit gate | State transition proposal | Memory writer, agent, UI |
| Audit | Protected append-only audit boundary | Event records | Component under investigation as sole audit source |
| Recovery | Recovery controller and root trust | Restore proposal | Untrusted runtime or model |

A component can hold more than one technical role only if its trust boundary and separation controls are explicit and independently reviewable.

## 3. Identity and principal model

Identity references are typed and non-interchangeable:
- **Principal:** user, service, agent or organization represented by the trust system.
- **Device:** hardware/software endpoint identity and attestation epoch.
- **Runtime:** specific execution host/runtime identity.
- **Surface session:** authenticated interaction session, not itself a principal.
- **Agent instance:** registered agent identity/key epoch and declared implementation version.
- **Adapter:** registered executable boundary and artifact provenance.
- **Tenant:** isolation/accounting boundary; it does not replace principal identity.

Every privileged action binds at minimum to principal, tenant/scope, execution, runtime, adapter, action digest and expiry. Missing or ambiguous binding denies dispatch.

Identity proof, authentication, authorization and capability are separate assertions. A valid identity does not imply permission.

## 4. Policy and capability decision

Policy evaluates:
- authenticated principal and assurance level;
- target/resource and operation;
- tenant and data scope;
- request origin and user gesture/consent;
- action risk and reversibility;
- current policy version;
- device/runtime trust and revocation epoch;
- data residency and egress constraints;
- resource and deadline budget;
- freshness and idempotency requirements.

Capability grant is narrow and attenuated:
- exact action class;
- exact resource/target or bounded allow-list;
- principal and execution binding;
- data read/write scope;
- expiry and maximum calls;
- egress and resource constraints;
- approval reference where required;
- revocation epoch and nonce/sequence binding.

Delegation can only reduce scope. No child agent, adapter or remote node can widen the grant.

## 5. Action envelope and runtime admission

The ActionEnvelope is a canonical, versioned description of the exact operation to be executed. It binds:
- action ID and schema version;
- principal, tenant, execution and runtime IDs;
- adapter ID/version and target;
- capability reference and policy decision reference;
- input digest and data classification;
- deadline, resource limits and cancellation token reference;
- idempotency key and replay/freshness metadata;
- user approval digest where required.

Runtime admission checks envelope schema, identity, capability, target, deadline, policy snapshot, replay state and resource reservation before dispatch. The adapter receives only the minimum scoped inputs and authority required for the operation.

Any material change to target, payload, operation, scope or side-effect class creates a new action digest and invalidates prior approval.

## 6. Agent lifecycle and delegation

Canonical agent lifecycle:

`DISCOVERED → REGISTERED → IDENTITY_VERIFIED → ADMITTED_FOR_SCOPE → ASSIGNED → RUNNING → RESULT_SUBMITTED → RESULT_VERIFIED → COMPLETED`

Exceptional states:
- suspended;
- revoked;
- expired;
- quarantined;
- failed;
- cancelled.

Agent manifest declares code/model provenance, version, skills, input/output contracts, resource budget, isolation profile, supported domains and trust requirements. Skill declarations are descriptive and do not grant authority.

Delegation contract:
1. parent task and principal binding are explicit;
2. child receives only required task data and an attenuated capability;
3. child execution ID and parent correlation reference are bound;
4. delegation depth, fan-out, time and resource budgets are bounded;
5. child result carries provenance and is independently admitted;
6. revocation propagates to descendants and pending dispatch;
7. same-agent self-consensus is not independent corroboration.

## 7. Runtime lifecycle and concurrency

Canonical execution lifecycle:

`CREATED → VALIDATED → ADMITTED → SCHEDULED → RUNNING → RESULT_PENDING → VERIFYING → COMMIT_PENDING → COMMITTED`

Terminal alternatives:
- rejected;
- cancelled;
- expired;
- failed;
- incomplete;
- quarantined;
- degraded.

Rules:
- lifecycle transitions are monotonic and version-checked;
- deadlines and cancellation propagate through descendants and adapters;
- retries require idempotency or explicit compensation;
- a partial external side effect is represented as an unresolved transaction, not a success;
- scheduler concurrency and queue budgets are explicit;
- resource exhaustion causes rejection or declared degradation;
- model/provider timeouts never bypass result validation.

## 8. Result attestation and verification

Attestation binds producer identity, adapter/runtime, execution, action digest, output digest, status, provenance references and sequence. It proves the attested producer emitted a particular artifact under a particular identity; it does not prove semantic truth.

Verification can include:
- schema and type validation;
- action/result binding;
- provenance completeness;
- independent domain checks;
- deterministic recomputation;
- formal checking where exact proposition/theory exists;
- empirical observation where the operation has real-world effects;
- policy postcondition validation.

The verification profile is selected by risk and operation class. A verifier exception, missing evidence or unsupported claim yields failed/indeterminate, never accepted.

## 9. State commit and transaction model

Only the state commit boundary may make authoritative persistent transitions.

Commit request includes:
- expected prior state version;
- proposed transition and output digest;
- principal/execution/action identity;
- result attestation and verifier references;
- idempotency key;
- transaction/compensation metadata.

Commit checks:
- all required verifiers accepted the exact artifact;
- identity and capability were valid at action time;
- no stale/replayed/duplicate transition exists;
- preconditions still hold;
- transaction is complete or explicitly modeled as pending/compensating;
- audit append is durable according to declared policy.

A failed commit leaves prior trusted state intact. Recovery cannot silently rewrite journal history.

## 10. Human approval and emergency controls

Approval is an independent, action-specific assertion binding:
- approver principal and assurance level;
- exact action digest and target;
- visible disclosure summary and material risks;
- scope, timestamp and expiry;
- policy version;
- optional dual-control/quorum requirement.

Approval is invalidated by material action changes or expiry. Silence is not approval.

Emergency stop and revocation have higher priority than ordinary task execution. Break-glass actions are narrow, time-limited, independently audited and reviewed after use.

## 11. Recovery and trust-root bootstrap

Recovery lifecycle:
`DETECT → CLASSIFY → CONTAIN → REVOKE → PRESERVE → RESTORE → RE-ATTEST → RECONCILE → MONITOR`

Recovery sources must be authenticated and integrity-checked. Restore only trusted artifacts from an authorized catalog. Recovered nodes receive a new epoch and must reconcile revocation state before privileged work resumes.

Recovery bootstrap cannot rely solely on the component being recovered. A documented offline/manual trust-root path is required for root compromise and cloud unavailability.

## 12. Cross-cutting failure semantics

| Condition | Required result |
|---|---|
| Identity/authentication invalid | deny and audit |
| Policy missing or ambiguous | deny |
| Capability absent/expired/revoked | deny |
| Approval digest mismatch | deny and request fresh approval |
| Action replay/duplicate | reject or return prior idempotent result |
| Adapter timeout before side effect | failed/expired |
| Adapter timeout with uncertain side effect | incomplete; reconcile before retry |
| Verifier exception | quarantine or indeterminate; no commit |
| State version conflict | reject and replan |
| Audit integrity failure | security incident; block affected privileged commit |
| Recovery artifact untrusted | quarantine and stop |
| Node partition with stale revocation | restrict to declared offline-safe action classes |

## 13. Decisions still requiring source-level reconciliation

This architecture resolves the intended authority model but not the implementation ownership conflicts. Before freeze, inspect and decide:
- whether `core/runtime.py`, `core/operational_runtime.py`, `core/hypersynth_runtime.py`, JARVIS runtime and `noryx7_runtime/engine.py` are distinct orchestration layers or overlapping facades;
- which state/journal implementation is canonical and how JARVIS state maps to it;
- whether capability issuance has exactly one authoritative broker;
- how existing RecoveryController APIs map to runtime recovery and ecosystem isolation;
- which audit chain is authoritative for cross-runtime actions;
- exact offline revocation freshness and action restrictions.

**Decision status:** proposed target architecture. Do not mark authority/runtime/state architecture frozen until the source-level reconciliation items are closed.
