# NORYX7 — Runtime constructor/call graph, retry ownership, offline durability and release-governance reconciliation

**Review date:** 2026-11-25  
**Reviewed branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source snapshot:** `d629cdd0472e81f8876d144ebb133fbbd6a0c7b9`  
**Mode:** architecture-only, bounded source and repository-tree reconciliation  
**Scope:** W01–W12; no runtime, test, dependency, workflow, configuration, deployment or frozen-baseline changes

## 1. Purpose and evidence discipline

This pass advances the prior ingress/effect and constructor/callsite reviews by joining the actual constructor contracts, route composition, state/recovery implementations, provider retry layers, agent assignment paths, global registries and release evidence.

The evidence classes remain distinct:

- **Source behavior:** directly visible in the inspected file at the exact source snapshot.
- **Repository inventory:** a path exists in the recursive tree; this does not prove its callers or runtime activation.
- **Architecture requirement:** a contract needed to reconcile the source paths; not represented as implemented.
- **Operational assurance:** requires deployment, multi-process, durable-storage, external-target or independently produced evidence not established by this source pass.

This is not a complete dynamic call graph. A bounded source inspection cannot prove the absence of uninspected callers, external reverse-proxy policy, production adapters or connected payment systems.

## 2. Constructor and authority map — W01/W02/W07/W08/W09

### 2.1 Identity and grant authorities are distinct objects

Inspected source anchors:

| Path | Blob SHA | Observed boundary |
|---|---|---|
| `core/identity.py` | `e6e8e5b03135251baca489643f86c7d81a755a08` | Ed25519 agent identity; local IdentityRegistry maps agent ID to public key; revoke removes the current mapping; optional trusted-identity critical section |
| `core/actions.py` | `5e2fc212abea2873bb471b12e6fe6f5021664e97` | AuthorizationAuthority issues short-lived one-shot HMAC grants bound to canonical action fingerprint, execution, principal and key fingerprint; ActionGate is a final fail-closed action boundary |
| `gateway/auth.py` | `fa456172c99b183dcb2acd0ec99303ec540d2583` | SessionAuthority issues/verifies HMAC browser sessions bound to client ID, expiry and nonce |
| `jarvis/security/authorization.py` | `dd7db5e133632061bbfbac88ed47bede27bc387c` | Separate JARVIS principal/capability/target grant authority |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` | GlobalIdentityAuthorizationFabric indexes session/device/role/capability/policy bindings; local in-memory index |

Positive controls must be retained: action grants bind exact canonical action content and execution identity; a configured IdentityRegistry is consulted at issue/verify/consume; consume-and-execute linearizes nonce consumption with identity revocation for the local registry; SessionAuthority validates token signature and expiry; the global fabric explicitly says its index does not grant authority implicitly.

The unresolved issue is not that these controls do not exist. It is that the inspected source defines multiple trust domains and issuer/consumer APIs without a demonstrated canonical principal-assertion adapter or shared lifecycle. A gateway client ID is not automatically an AgentIdentity, tenant principal, device identity or workload identity. A global session binding is not automatically the same record as the core IdentityRegistry or JARVIS authorization state.

**Architecture requirement:** normalize all authenticated ingress into a signed/verified PrincipalAssertion with issuer, subject, tenant, session, device/workload, audience, authentication assurance, issued/expiry times, key ID, policy epoch, revocation freshness and delegation chain. Each authority must declare whether it is an issuer, verifier, registry, capability decision point or cache. Define revocation propagation and stale-cache limits across processes and planes.

### 2.2 Constructor injection and lifetime remain an architecture boundary

The source contains explicit optional injection points:
- AuthorizationAuthority accepts an optional IdentityRegistry; when omitted, grants may be issued without principal binding (the API permits an empty principal identity).
- Runtime StateJournal accepts optional verifier, IdentityRegistry and runtime ID, while signed mode requires a verifier.
- RuntimeRecovery can inherit verifier and registry from its journal, or accept explicit overrides.
- AgentCoordinator can construct its own ActionGate when none is injected, creating a local PolicyEngine, SecurityBoundary and RuntimeLimits.
- ProviderExecutionGateway and ResilientProviderExecutor can each create a fresh ProviderRouter when none is supplied.
- OfflineRuntime constructs its own OfflineSyncQueue internally; the queue has no injected durable repository.
- Web app caches one OperationalNORYXRuntime and one NoryxGateway per process using lru_cache; this does not establish cross-worker shared authority or state.

These are not automatically defects: optional injection supports tests and standalone use. The architecture must distinguish test/local construction from production composition and specify a single composition root, allowed constructor profiles, required shared instances, secret/key source, process lifetime, replica scope and startup failure behavior.

## 3. Ingress and execution convergence — W01/W02/W08

Source anchors:
- `web/app.py` SHA `a03d012d6f9f2fdbfb8a5e64397511e5ac692360`
- `gateway/server.py` SHA `b434cdbe118ecea48029adcd2c954fa1ac14461c`
- `gateway/auth.py` SHA `fa456172c99b183dcb2acd0ec99303ec540d2583`

The FastAPI surface defines:
- `POST /v1/session` → gateway SessionAuthority bootstrap flow;
- `POST /v1/execute` → Bearer token required, then gateway RuntimeAdapter;
- `POST /api/chat` → directly constructs TaskSpec and invokes OperationalNORYXRuntime.run_hypersynth;
- health routes use separate initialization paths.

The separate `NoryxGateway` HTTP server also exposes session and execute routes with Bearer verification. The direct `/api/chat` route does not itself invoke SessionAuthority. This is a route-level divergence, not proof of an exploitable unauthenticated deployment: upstream authentication, routing and proxy policy are not established by these files.

**Architecture requirement:** all public ingress must converge on a shared authenticated request envelope and authorization/audit boundary before planning or tool dispatch. Any trusted upstream authentication must be explicit, with trusted-hop identity, header stripping/rewriting, channel authentication, audience and replay rules. Health and public read-only routes need a separate minimal disclosure policy.

## 4. State, effect, and recovery authority — W02/W03/W08/W09

### 4.1 Two journals have different semantics

| Path | Blob SHA | Role observed |
|---|---|---|
| `noryx7_runtime/state.py` | `444aba1fb92a4bb70ee2ee31b23d3946680bb630` | Runtime in-memory reservation and signed attestation journal; reserves before dispatch; verifies agent identity/key and attestation chain on append |
| `core/state.py` | `f1dd791359038d799a63852ea850ce7f3d738148` | Verified NORYX state commits; optional StateJournal injection; rehydrates commits when a journal is supplied |
| `core/state_journal.py` | `4ea3419cb05a4edbb228966ea2584894197caa83` | SQLite WAL/FULL synchronous durable state-commit journal; canonical digest, sequence validation and recovery |
| `core/recovery.py` | `226193d08b0b8c57f275125e25b7823886ea163d` | In-memory recovery state machine with epoch and serialized run_if_normal critical section |
| `noryx7_runtime/recovery.py` | `ecd5743a494a150e13556e5c3932b77a6b08aaa7` | Validates runtime journal sequence, step uniqueness, signatures, identity, runtime ID and attestation chain |

These are useful but not interchangeable. Runtime StateJournal's reservations/attestations and core StateJournal's verified state commits are separate persistence domains. SQLite durability in the latter does not make the former durable. RuntimeRecovery validates its own journal type and does not by itself coordinate the SQLite state-commit journal. RecoveryController is process-local and its epoch is not shown as a shared distributed fencing token.

**Architecture requirement:** define one operation transaction envelope and explicit cross-journal protocol: reservation, dispatch attempt, effect receipt, verified result, attestation, state commit, recovery checkpoint and compensation. State exactly which writes are atomic together, which are saga steps, and how crash recovery resolves each intermediate state. Do not claim a distributed ACID transaction where only local locks or one SQLite transaction exist.

### 4.2 External effect certainty must outlive an exception

RuntimeEngine reserves an action step before adapter dispatch and later verifies/attests output. If dispatch may have reached an external target and later verification, attestation or commit fails, local failure cannot establish that the target did nothing. A reservation is not an external receipt; a journal rollback is not compensation.

The canonical lifecycle must distinguish:
`NOT_DISPATCHED`, `DISPATCH_UNKNOWN`, `TARGET_ACCEPTED`, `EFFECT_OBSERVED`, `RESULT_ADMITTED`, `STATE_COMMITTED`, `COMPENSATION_REQUIRED`, `COMPENSATED`, and `INDETERMINATE`.

Every transition must carry logical operation ID, step ID, attempt ID, dispatch ID, target idempotency key, target identity, effect class, acknowledgement/evidence reference, timestamps, policy epoch and recovery owner.

## 5. Provider graph and retry ownership — W02/W05/W08/W11

Source anchors:
- `core/provider_router.py` SHA `9bd085ddaf660ac53039dd80eb6c822cb9226eba`
- `core/provider_execution.py` SHA `93e63c085321e2b4413dbcf4878a4c4f6a82953e`
- `core/provider_resilience.py` SHA `a678329d5b29a184a7b26ca9bc71ff0a232df136`

The three classes represent separate execution semantics:
1. ProviderRouter resolves the first matching provider and retries another provider after any handler exception until candidates are exhausted.
2. ProviderExecutionGateway resolves one provider, builds an ExecutionFabric adapter and invokes the supplied authorization callback immediately before execution; it does not use ProviderRouter.execute failover.
3. ResilientProviderExecutor has a bounded attempt loop, excludes failed providers and records local attempt outcomes; PermissionError is terminal.

The action IDs differ between gateway and resilience paths: gateway builds a provider/principal/capability ID reused for that route; resilience adds attempt number. If these layers are nested by callers, local retry budgets can multiply, and exceptions after target dispatch are currently too coarse to distinguish safe retry from unknown effect. The bounded source pass has not proven a complete dynamic caller graph or a universal single retry owner.

**Architecture requirement:** one logical ProviderOperationCoordinator owns retries across model, provider, tool, scheduler and recovery layers. It must receive typed outcome classes, not raw exceptions alone; calculate the total attempt budget; bind unique attempt IDs; reauthorize each attempt; preserve target idempotency; enforce deadline, budget, cancellation, residency and provider-trust constraints; and reconcile unknown outcomes before retrying non-idempotent effects.

## 6. Agent fabric, assignment and execution lineage — W04/W05/W07/W11

Source anchors:
- `core/coordination.py` SHA `c5743872a5b50765db04e4a42739e9ad238ad983`
- `core/agent_fabric.py` SHA `3704dd7bf66815274cc319c9583c45ae575f3d36`
- `core/agent_mesh.py` SHA `25c9162750708e53742862f9f413fdf5200ca08f`
- `core/operational_fabric.py` SHA `a2f6a46c1fdec47f3fe1f95f6c20f9848673f127`
- `noryx7_runtime/scheduler.py` SHA `5d87d38e17c93dd26975119bb3af1dddd6c132b9`

AgentCoordinator:
- can construct a default local ActionGate;
- assigns only `plan.steps[:max_agents]`, so plans with more steps than the bound need explicit continuation, rejection or batching semantics;
- generates a new execution ID in execute rather than preserving a caller-supplied parent execution lineage;
- runs assignments sequentially;
- validates live agent identity before execution and again before result admission;
- verifies result identity, execution ID, status, stage and output;
- consensus requires distinct agent IDs, one task ID and exactly equal outputs.

These are meaningful local boundaries. However, exact-output equality is not a universal consensus rule for probabilistic, evidence-based, numeric, multimodal or domain-specific tasks. AgentMesh role selection, AgentFabric skill selection, OperationalAgentFabric supervisor admission, AgentCoordinator and RuntimeEngine remain distinct paths. Scheduler topological ordering is not a parallel executor, and agent identity diversity does not prove independent provider/model/source/failure domains.

**Architecture requirement:** canonical parent/child execution lineage with request → plan → DAG node → assignment → agent invocation → tool/provider attempt → result → admission IDs. Preserve parent execution ID and explicit child IDs; never silently truncate steps. Define bounded concurrency, leases, capacity reservations, fairness, cancellation, partial completion, join rules, retries and consensus semantics by output type. Qualification and authorization remain separate from routing.

## 7. Offline durability and acknowledgement protocol — W03/W08/W09

Source anchors:
- `core/offline.py` SHA `6d0c5a76134fa679279406da1a514e628240debd`
- `core/offline_anchor.py` SHA `a130043ae7dff949b072ae97fd00137d8051d2ea`
- `core/offline_adapters.py` SHA `bcdd8210b71f60a5f07f50b8975798fdd8c6b6f3`

Positive behavior: snapshots are integrity checked and authenticated by an injected callback; age, principal, capability and policy are checked; a monotonic anchor can reject rollback; payloads are encrypted with execution-specific AAD; payload and ciphertext digests are checked; reconnect requires authenticated and verified channel flags; remote state-version conflicts are detected.

Important limitation: OfflineSyncQueue stores records and sequence in process memory. OfflineRuntime constructs it internally. acknowledge/acknowledge_synced removes records from that volatile map. The SQLite monotonic snapshot anchor protects accepted snapshot epochs but does not persist the outbox, execution result, remote acknowledgement or deletion protocol. In execute(), a caught exception after the envelope was enqueued calls acknowledge(), removing the queued envelope; if execute() already caused an external effect, there is no durable reconciliation record demonstrated by this queue.

**Architecture requirement:** durable encrypted outbox and inbox, crash-safe sequence, stable record IDs, append-before-effect or an explicitly recoverable dispatch protocol, signed remote receipt, idempotent replay, durable acknowledgement, tombstones/retention, conflict resolution and reconciliation of unknown effects. Persist key ID/version and rotation/revocation metadata; define behavior when local key material is unavailable. Snapshot anti-rollback, queue durability and target idempotency are three separate guarantees.

## 8. Global memory, placement and cross-node trust — W03/W05/W08/W09

`ecosystem/global_fabric.py` defines six memory levels and record metadata with payload/provenance digests and replica IDs. The inspected GlobalMemoryFabric and GlobalIdentityAuthorizationFabric are bounded in-memory indexes. A replica list is metadata, not proof that replicas exist, have acknowledged writes, share encryption policy or can be recovered. ResourceRouter and global-scale primitives likewise need actual placement leases, capacity evidence, replication protocol, quorum/consistency semantics and node attestation before their architectural intent can be treated as distributed guarantees.

**Architecture requirement:** separate record metadata from payload custody; define encrypted storage adapters, key ownership, tenant isolation, residency, replication acknowledgements, version vectors/conflict policy, deletion propagation, retention/legal hold, offline merge, node attestation, placement lease and failure-domain model. A placement decision must reserve a real resource and be revocable/fenced, not merely choose a device/edge/cloud label.

## 9. W12 business, financial and public-impact authority

The recursive source tree includes `core/supply_chain.py` (SHA `4cf383541d1623a3fbb9cecd70f4d4dd8cfbb9f5`), which verifies signed artifact manifests against explicitly trusted Ed25519 keys and artifact bytes. This is a supply-chain integrity primitive, not a financial ledger.

The bounded filename inventory surfaced architecture-level business/project/impact material and no obvious production implementation path named for ledger, payment, escrow, wallet, billing, donation, carbon or accounting. That is an inventory observation only; functionality may be represented under other names or external adapters. The existing business/project architecture remains a proposal, not proof of a production financial execution stack.

**Architecture requirement:** before any real funds movement, define double-entry ledger, immutable journal, segregated customer/third-party/company balances, payment-provider adapter, escrow custody/legal owner, authorization and dual control, consent/beneficiary/purpose, fees/commission calculations, refund/chargeback/dispute, sanctions/fraud controls where applicable, reconciliation, tax/accounting exports, audit, privacy and incident recovery. Agents may propose or calculate but cannot directly hold or move funds without an explicitly authorized, independently controlled transaction service.

Public/environmental impact needs an independent evidence model: baseline, counterfactual, additionality, leakage, permanence, uncertainty, double-count prevention, geographic/time scope, verifier independence and correction/reversal. Activity counts, money raised, kilograms collected or trees planted are not interchangeable with verified net outcomes.

## 10. Release and deployment evidence — W09/W11

Repository inventory includes seven GitHub Actions workflows and a signed-artifact manifest verifier. The inspected `.github/workflows/noryx7-foundation.yml` (SHA `80963b0a328724bad04908ee2db72ce71dd10ae6`) runs compile, pytest and Android browser test steps for configured events and publishes a workflow summary/artifact. This defines a CI job; it does not by itself establish signed release provenance, artifact promotion, deployment approval, environment attestation, rollback or production health evidence.

The supply-chain verifier trusts a locally provided signer-key set. How those roots are provisioned, rotated, revoked and protected is outside that class. The inspected manifest schema does not itself bind build workflow identity, source commit, dependency SBOM, builder environment, policy/test evidence, approval quorum, deployment target or rollback plan.

**Architecture requirement:** signed provenance chain from source commit to build, artifact, test evidence, approval, promotion, deployment, runtime health and rollback. Bind every evidence item to exact artifact digest and environment. Protect release keys independently of the system being released; require staged promotion, independent approval and immutable audit evidence. Self-improvement must not modify its own trust roots or approve its own release.

## 11. Cross-workstream closure dependencies

| Dependency | Affected streams | Closure evidence still required |
|---|---|---|
| Principal and authority normalization | W01/W02/W07/W08/W09 | issuer/subject/tenant/session/device/workload schema, composition root, shared revocation/freshness rules, route coverage |
| Operation/effect lifecycle | W02/W03/W05/W08/W09/W11 | durable attempt/effect receipts, idempotency, uncertain outcome and compensation protocol |
| State and recovery coordination | W03/W08/W09 | cross-journal transaction model, durable checkpoints, restart and multi-replica recovery |
| Provider retry ownership | W02/W05/W08/W11 | caller graph, one retry owner, classified failures and end-to-end budget |
| Agent DAG/lineage | W04/W05/W07/W11 | no truncation, parent-child identity, concurrency/lease/cancel/join semantics |
| Offline queue continuity | W03/W08/W09 | durable outbox/inbox, receipt, acknowledgement and replay/reconciliation |
| Global memory and placement | W03/W05/W08/W09 | actual storage/replication/lease/attestation adapters and consistency semantics |
| Financial/public-impact authority | W12 plus W07/W08/W09 | ledger/payment/escrow control, independent accounting and impact verification |
| Release provenance | W09/W11 and all planes | source-to-artifact signed attestations, promotion, rollback and operational acceptance |

## 12. Disposition

- W01–W12 remain **PARTIAL**.
- Existing ADR-B56–B62 remain the home for ingress/effect/release evidence decisions; reuse existing authority, retry, agent and W12 decision records rather than creating duplicate IDs.
- No ADR is accepted or frozen by this document.
- No runtime, test, workflow, dependency, configuration, deployment or frozen-baseline file is changed.
- No tests or CI runs are claimed by this architecture pass.
- The next architecture pass must close the remaining constructor/consumer map, especially production composition roots, provider nested callers, parent-child agent execution lineage, durable offline inbox/outbox, financial adapter boundaries and release promotion/rollback evidence.
