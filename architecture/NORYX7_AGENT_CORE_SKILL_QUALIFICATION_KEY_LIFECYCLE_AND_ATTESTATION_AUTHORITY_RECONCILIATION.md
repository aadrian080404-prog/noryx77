# NORYX7 — Agent Core, Skill Execution, Key Lifecycle and Attestation Authority Reconciliation

**Date:** 2026-11-25  
**Repository:** `aadrian080404-prog/noryx77`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Inspected source HEAD:** `773cd0186e58a8df0f399dbd01157f49a665684c`  
**Mode:** architecture-only source reconciliation  
**Disposition:** W01–W12 remain PARTIAL.

This document records bounded source behavior and architecture requirements. It does not claim production wiring, deployment assurance, complete caller coverage or workstream closure. No runtime, test, dependency, workflow or configuration file is changed.

## 1. Exact source anchors

| Source | Blob SHA | Bounded source observation |
|---|---|---|
| `core/agent_core.py` | `f9ad4e3e7bc03e03ddcce4df563e551d4226d747` | AgentCore lifecycle, brain protocol, sequential step loop, optional authorization hook, boolean verification and sorted in-process registry. |
| `core/agent_identity.py` | `cc1076ef80a0e88066ee77155d6c630844907cd7` | Static mission profiles and agent-specific behavioral instructions; not an identity credential or authorization grant. |
| `core/agent_skills.py` | `281d294ee0142a8dd33db5d61f634f95943db231` | Bounded skill registry; declarative skills may use a default no-op handler; registration explicitly does not grant authority. |
| `core/key_lifecycle.py` | `9cdb83a93dc75df6b1fc9041f75894cf960328a5` | ACTIVE/RETIRING/REVOKED key metadata state machine; raw key material is delegated to an external KMS/HSM boundary; records are in-memory. |
| `core/attestation.py` | `48a5145b33c73c9e8d3b1f0051050dd97f89786f` | External attestation verifier interface and runtime measurement/expiry/nonce binding; concrete production verifier is not supplied in this module. |
| `noryx7_runtime/attestation.py` | `b417bdb09f5ad920f7b6cf96910aea5c6447ac2a` | Ed25519 operation attestations, identity-bound verifier, canonical signed message and ordered chain verifier. |
| `core/recovery.py` | `226193d08b0b8c57f275125e25b7823886ea163d` | Process-local recovery state machine and epoch; serializes a bounded critical operation with transitions. |
| `noryx7_runtime/recovery.py` | `ecd5743a494a150e13556e5c3932b77a6b08aaa7` | Runtime-journal recovery validates entries, sequence, duplicate steps, runtime identity, signatures, identity binding and attestation chain. |
| `jarvis/core/provider.py` | `caee59075b8c4f317922f615ee5c7d6f1d3dde71` | JARVIS provider adapter returns an ActionResult bound to the requested plan step; adapter is not itself an authority. |
| `jarvis/providers/base.py` | `386a046a7f04a16ae7c2a29ad99d76a041d8e3f3` | Separate minimal model-provider protocol. |

## 2. Agent Core: sequential local lifecycle, not distributed scheduling

### Observed
- `AgentCore.run` acquires one re-entrant lock for the entire understand → plan → authorize → act → verify → reflect → respond path. Calls on the same instance are serialized; this class does not execute plan steps concurrently.
- Plan steps are iterated sequentially and bounded by `max_steps`.
- The authorization hook is optional. When supplied, it must return truthy; when absent, this class does not perform its own authorization decision.
- The brain's `verify` method returns a boolean. The final response also carries a boolean `verified` field supplied by the brain.
- `AgentRegistry` is bounded and process-local; snapshots are sorted by agent ID.
- Failure moves the agent to FAILED and requires an explicit reset before reuse.

### Boundary interpretation
The optional hook is not evidence of a system-wide authorization bypass: other ingress, runtime or ActionGate layers may authorize callers. It is, however, proof that AgentCore alone does not guarantee authorization. A caller/constructor map must show which production compositions inject the hook and which execution paths instead enforce a downstream canonical gate.

A boolean verification result is not a proof object. The class does not bind the verifier identity, evidence references, policy version, test method, confidence, source digest or independent-review status to that boolean.

### Architecture requirement
Define one mandatory ExecutionEnvelope and AuthorizationDecision contract for every agent invocation. AgentCore must either require an authorization capability at construction or be explicitly restricted to a non-executing planning mode. Replace bare verification booleans at trust boundaries with typed VerificationRecord objects bound to evidence, verifier identity, scope, method, policy version and execution digest. Keep the local agent state machine separate from the global DAG scheduler.

## 3. Skill registry: declarative presence is not executable capability

### Observed
- `AgentSkillRegistry` is bounded and lock-protected.
- A skill's handler defaults to `_default_skill_handler`, which returns `None`.
- The module explicitly states skills describe capabilities and do not grant authority.
- A registered skill name/description therefore does not establish that a meaningful implementation exists or that an agent is qualified to perform the work.

### Architecture requirement
Represent skill lifecycle explicitly: DECLARED, IMPLEMENTED, QUALIFIED, AUTHORIZED, AVAILABLE, DEPRECATED, REVOKED. A no-op handler must be represented as declarative-only and excluded from executable capability claims. Qualification evidence must include benchmark/task scope, version, recency, evaluator, failure modes and revocation. Authorization remains a separate decision.

## 4. Two attestation planes must not be conflated

### 4.1 Runtime measurement binding — `core/attestation.py`
The module defines an external verifier interface. RuntimeIdentity validates measurement format, time window and non-empty nonce, then accepts the attestation only when the injected verifier returns exactly True. It stores runtime ID, measurement and nonce in the object and can produce a binding digest.

This is a strong fail-closed adapter boundary, but the module does not provide a concrete production verifier, hardware-root source, freshness/replay store, remote revocation feed or durable binding registry. The nonce is validated as present but cross-instance replay prevention is not established by this class.

### 4.2 Agent operation attestation — `noryx7_runtime/attestation.py`
This plane signs a canonical message containing execution, principal, step, agent, key fingerprint, action/output digests, verification marker, prior-attestation digest, runtime and provenance fields. Ed25519 implementations and an identity-bound verifier are present. The chain verifier enforces consistent execution/principal/runtime identity and prior-digest continuity.

This proves cryptographic integrity and signer identity within the configured trust boundary. It does not independently establish that the action was authorized by every relevant policy, that the external effect happened, that the output is true, or that the evidence source is independent.

### Architecture requirement
Create a layered AttestationEnvelope that references (rather than conflates):
1. workload/runtime measurement attestation;
2. agent identity and key epoch;
3. execution/action authorization decision;
4. operation/result attestation;
5. effect observation and independent verification;
6. durable commit/recovery checkpoint.

Each layer needs a separate issuer, verifier, key domain, expiry/revocation semantics and evidence type. Bind them through immutable digests and explicit references. Never let an agent's self-reported `verified=True` substitute for independent verification.

## 5. Key lifecycle and recovery: useful local state machines, incomplete distributed authority

### Observed
- `KeyLifecycle` tracks key ID, version and state under a local lock; it does not store raw key material and exposes an external KMS/HSM interface.
- Its metadata registry is an in-memory dictionary. Persistence, multi-process consistency, KMS binding, rotation completion, old-version decrypt policy and revocation propagation are not implemented in this class.
- `RecoveryController` has explicit incident → lockdown → trusted-only → recovery → verified → normal transitions and a monotonic process-local epoch.
- `run_if_normal` serializes a critical operation with recovery transitions within that controller instance.
- `RuntimeRecovery` validates the runtime StateJournal and its attestation chain. It does not establish coordinated recovery across the separate SQLite verified-state journal, provider side effects, offline queues, distributed replicas or every runtime process.

### Architecture requirement
Unify recovery as a coordinated protocol, not a shared enum. Define recovery authority, epoch/fencing scope, journal participants, durable checkpoints, KMS/key-version dependencies, remote revocation, provider-effect reconciliation, replica quorum and operator approval. Specify crash points and restart behavior for every transition. Local lock linearization must not be described as distributed atomicity.

## 6. JARVIS provider boundaries

The inspected JARVIS provider protocol is intentionally small: providers accept a request and plan step and return a typed ActionResult that must match the step. This is an adapter contract, not a canonical model-provider, tool-execution or effect-reconciliation authority. Reconcile it with the core ProviderRouter, ProviderExecutionGateway, ResilientProviderExecutor and the model-provider protocol without collapsing proposal generation and external action into one privilege.

## 7. W01–W12 impact

| Workstream | New clarification | Remaining evidence |
|---|---|---|
| W01 Identity | Runtime measurement and agent operation attestations are distinct trust planes. | One issuer/verifier map, key epoch and revocation propagation across runtime, agent, device and provider. |
| W02 Runtime | AgentCore serializes a local run; separate recovery controllers and journals exist. | Canonical execution/effect lifecycle and coordinated durable recovery. |
| W03 Memory | Key metadata and recovery epochs are local state in these modules. | Durable custody of memory keys, snapshots, tombstones and recovery checkpoints. |
| W04 Agent Fabric | AgentCore uses sequential steps and optional authorization; skill registry may contain no-op handlers. | Mandatory auth boundary, qualified executable skills, DAG concurrency and typed independent verification. |
| W05 Routing | AgentRegistry ordering is lexical, not a capacity or competence score. | Qualification-aware selection, capacity leases, deadline and budget-aware placement. |
| W06 NEXUS | Boolean verification is not a source-grounded claim/evidence object. | VerificationRecord linked to ClaimRecord, exact source span, authority and contradiction graph. |
| W07 MIRROR WORLD | Attestation integrity does not validate model fidelity. | Experiment provenance, real-world calibration, independent observations and uncertainty. |
| W08 Interfaces | Provider adapter result matching is not external-effect proof. | Surface identity, action receipt, observed state and effect reconciliation. |
| W09 Security | Ed25519 operation chain and external runtime verifier interfaces exist. | Production roots, KMS/HSM adapter, replay prevention, revocation and cross-plane trust policy. |
| W10 Specialist Domains | Skill labels are not measured qualification; default handlers may be no-op. | Executable implementation proof, benchmarks, credential scope and evaluator independence. |
| W11 Operations | Recovery and attestations validate bounded local journal scope. | Cross-journal recovery, SLO/incident evidence, release/deployment attestations. |
| W12 Ecosystem | These modules do not establish finance or impact authority. | Ledger/payment controls and independently verified public-impact evidence. |

## 8. Shared architecture decisions to reconcile (no duplicate ADR IDs)

- Mandatory authorization profile for AgentCore and planning-only profiles.
- Typed VerificationRecord and independent verifier trust.
- Declarative versus executable versus qualified skill lifecycle.
- Runtime measurement versus agent operation attestation layering.
- KMS/HSM ownership, key metadata durability, nonce replay and revocation.
- Recovery coordination across runtime journal, SQLite state journal, provider effects, offline queue and distributed memory.
- Provider adapter and tool execution authority boundaries.

Use existing open ADRs and the current decisions backlog; do not infer new ADR identifiers from this document.

## 9. Closure gates

W01–W12 remain PARTIAL until the following are evidenced where applicable:
- Every production AgentCore constructor/caller is mapped and its authorization profile is explicit.
- Every executable skill has a real handler, qualification evidence and separate authorization.
- Attestation issuers, verifiers, trust roots, key versions, nonce/replay controls and revocation paths are mapped.
- Runtime and operation attestations are linked but remain semantically distinct.
- Recovery is crash-tested across all participating journals and external effects with explicit fencing scope.
- Verification records bind evidence and independent verifier identity rather than a bare boolean.
- Evidence is tied to immutable source revision and exact assurance scope.

**Disposition:** architecture discovery only. No integration, test modification, workflow change, merge or deployment is authorized by this pass.
