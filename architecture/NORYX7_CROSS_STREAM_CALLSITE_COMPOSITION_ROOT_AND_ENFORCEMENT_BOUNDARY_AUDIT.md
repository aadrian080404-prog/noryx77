# NORYX7 — Cross-Stream Call-Site, Composition-Root and Enforcement-Boundary Audit

**Audit date:** 2026-11-26  
**Architecture branch snapshot:** `b23206485241b9b4f51ad9b3db3a5f921dfe867c`  
**Scope:** source inspection only; no runtime, test, dependency, workflow, deployment or configuration changes.  
**Disposition:** architecture reconciliation; W01–W12 remain PARTIAL.

## 1. Method and evidence limits

This pass follows concrete composition roots, constructors, route handlers and dispatch/verification boundaries rather than treating class presence as integration. The exact source blob SHAs are listed below. The branch tree was inspected recursively and was not truncated. Findings are limited to these files and call paths; an uninspected external adapter or deployment override is not ruled out. No tests were executed in this pass.

## 2. HTTP ingress and runtime composition

### 2.1 Deployed Render entry point

`render.yaml` starts `uvicorn web.app:app`, not `python -m gateway`. The web composition root in `web/app.py` builds a cached `OperationalNORYXRuntime` by:
1. requiring `OPENROUTER_API_KEY`;
2. creating `OpenRouterAdapter`;
3. creating `ModelFabric`;
4. injecting that fabric into `OperationalNORYXRuntime`;
5. optionally passing `NORYX7_STATE_JOURNAL_PATH`.

The same cached runtime object is passed into `RuntimeAdapter(runtime=get_runtime())` by `get_gateway()`. Thus the deployed web application intentionally shares one runtime instance across its two HTTP interaction paths.

### 2.2 Two HTTP execution paths

| Route | Auth boundary | Runtime path | Source observation |
|---|---|---|---|
| `POST /api/chat` | No gateway session check in this handler | `get_runtime() → heartbeat_agents() → run_hypersynth(TaskSpec)` | Direct application chat path |
| `POST /v1/session` | Bootstrap token → HMAC-signed short-lived session | `get_gateway() → NoryxGateway.create_session()` | Session issuance path |
| `POST /v1/execute` | Bearer token → `SessionAuthority.verify()` | `NoryxGateway.execute() → RuntimeAdapter.execute() → run_hypersynth(TaskSpec)` | Session-protected gateway path |
| `GET /v1/health` | Gateway construction/health only | `get_gateway().health()` | Not an execution authorization proof |
| `GET /health` | No gateway session | `get_runtime().heartbeat_agents()` | Runtime/agent liveness view |

The two chat paths converge on the same cached runtime in this web composition, but they do not share the same ingress authentication contract. Route parity, rate limits, principal attribution and audit semantics must therefore be specified explicitly; shared runtime object identity alone does not establish equivalent ingress policy.

### 2.3 Session label versus enrolled principal

`SessionAuthority.issue()` signs a payload containing caller-supplied `client_id`, expiry and nonce. `verify()` authenticates the HMAC and expiry and returns that payload. `RuntimeAdapter.execute()` copies `client_id` into task constraints as `_noryx7_client_id`; the inspected adapter does not resolve that label to an enrolled device/principal or bind it to an identity key, device attestation, delegation grant or capability scope.

This is a boundary distinction, not a claim that HMAC is broken: the session proves possession of the configured gateway secret and integrity of the issued label, not the real-world or cryptographic identity of the named client. A canonical PrincipalAssertion and audience/scope/epoch check are still needed at the ingress-to-runtime boundary.

### 2.4 Standalone gateway constructor mismatch

`gateway/__main__.py` calls `NoryxGateway()`. That constructor defaults to `RuntimeAdapter()`; the adapter defaults to `OperationalNORYXRuntime()`; the latter explicitly raises `model_fabric_required_for_operational_agents` when no fabric is supplied. Therefore the inspected standalone `python -m gateway` default composition cannot initialize without a runtime adapter/model-fabric injection. This does **not** establish a defect in the deployed Render entry point, which uses `web.app` and injects the already-built runtime. The architecture must distinguish the supported production composition root from the standalone convenience entry point and either inject the same factory or fail at startup with an explicit supported configuration.

## 3. Canonical runtime and execution-plane divergence

- `web.app.get_runtime()` composes `OperationalNORYXRuntime`, which extends `NORYXRuntime`; its request path enters `run_hypersynth()` and the HYPERSYNTH kernel.
- `core/hypersynth_runtime.py` creates its own `VerificationEngine`, `ActionGate`, `ToolExecutor` and capability registry, then injects those into `Hypersynth`.
- `core/system_fabric.py` defines `CanonicalSystemFabric` and validates object identity for selected runtime, tool, verifier, authority and identity objects. The inspected web composition root does not construct or inject this fabric.
- `noryx7_runtime.engine.RuntimeEngine` is a separate execution plane with its own scheduler, adapter, attestation signer, identity registry, replay guard and optional `noryx7_runtime.state.StateJournal`. The inspected web runtime composition does not instantiate this engine.
- `core.runtime.NORYXRuntime` optionally constructs `core.state_journal.StateJournal` only when a path is supplied; the HYPERSYNTH path uses the runtime's own memory/state/audit abstractions. The RuntimeEngine journal and core journal have different APIs and semantics.

**Architecture consequence:** “canonical runtime” currently refers to multiple concrete execution/state paths depending on the entry point. The contract must name the authoritative execution plane per surface, then define explicit adapters and proof obligations before any claim of universal composition. Do not merge lifecycle enums or journals merely because their names overlap.

## 4. Verification, evaluation and result-admission consumers

- `VerificationEngine` is directly instantiated by `NORYXRuntime` and `HypersynthRuntime`, and injected into `ToolExecutor` and `Hypersynth`. It is a structural/contract verifier at these call sites; its successful return is not independent semantic truth.
- `EvaluationMatrix` accepts `EvaluationResult` records and aggregates their supplied pass/score/evidence fields. The inspected runtime composition does not inject an evaluator identity or a campaign executor into result admission.
- `core/evaluation_campaign.py` creates case/holdout structures; this is distinct from executing a campaign and independently attesting the raw results.
- The HYPERSYNTH subtask gate and UIF assessment contribute commit-eligibility signals, but those signals do not themselves authenticate source claims or qualify domain expertise.

**Required convergence:** define separate `StructuralVerification`, `SemanticAdmission`, `EvidenceAttestation` and `EvaluationCampaignReceipt` records. A structural pass must never be silently promoted into semantic correctness or a calibrated probability.

## 5. Tool and research acquisition boundary

`HypersynthRuntime` calls `install_frontier_capabilities(self.tool_executor)`; the web research capability is registered in the same `CapabilityRegistry` that the `ToolExecutor` executes through the `ActionGate`. This establishes an action-authorization path for invoking the tool, but it does not by itself establish destination authorization or socket-level network egress enforcement.

`WebResearchCapability` is constructed without an injected `EgressPolicy`/network enforcement adapter in this composition. Therefore the following remain separate gates: (a) principal authorization to invoke research, (b) URL/destination authorization, (c) DNS/IP and redirect validation at each hop, (d) bounded acquisition, (e) source custody and publisher authority, and (f) claim-to-span entailment. Do not treat the ActionGate as a substitute for network egress enforcement.

## 6. Standalone assurance components and operational consumers

| Component | Source-level role | Composition-root boundary |
|---|---|---|
| `SecureBootChain` | Stage/digest bookkeeping and admission helper | Not injected by the inspected web/OperationalNORYXRuntime composition; admission must be bound to a trusted ordered measurement chain |
| `AlertRouter` | Creates/stores alert records and chooses channels from policy | No delivery adapter/acknowledgement/incident owner is supplied by the inspected runtime composition |
| `ImprovementPipeline` | Local staged proposal state machine | External admission transition is not bound here to a signed receipt for the exact tested artifact |
| `GlobalControlPlane` / `CellRegistry` | In-process region/cell health and capacity selection | Not injected into the inspected web runtime; selection is not a fleet-wide reservation |
| `ElasticComputeFabric` | In-process available-capacity accounting | Acquire/release has no durable lease ID, owner, TTL, fencing token or recovery protocol |
| `GlobalMemoryFabric` / `GlobalIdentityAuthorizationFabric` | In-process record and authorization indexes | Replica labels/index state are not durable replication or issuer freshness/revocation proof |
| `CanonicalSystemFabric` | Object-identity consistency assertion | Not established as the actual composition root for the deployed web routes |

The bounded conclusion is that these classes are not shown as connected to the inspected web composition root; it is not a repository-wide or external-system absence claim.

## 7. Provider dispatch ownership

The source tree contains three distinct provider execution abstractions:
- `ProviderRouter.execute()`: direct provider resolution and execution;
- `ProviderExecutionGateway.execute()`: wraps a provider in an `ExecutionFabric` adapter with per-call authorization;
- `ResilientProviderExecutor.execute()`: owns a separate bounded retry/failover loop.

The inspected web composition root does not inject one shared instance or a single operation/effect coordinator across these paths. A provider timeout/exception is not proof that the remote side effect did not occur. The canonical operation ID, attempt ID, idempotency key, uncertain-effect state, authenticated effect receipt and retry owner must be defined once and propagated through each adapter.

## 8. Concurrent W01–W12 implications

| Workstream | Concrete call-site/consumer delta | Closure item |
|---|---|---|
| W01 Identity/trust | HMAC session label is not enrolled principal; no device/principal resolution in RuntimeAdapter path | PrincipalAssertion, audience/scope/epoch and device binding at every ingress |
| W02 Runtime/orchestration | Web HYPERSYNTH path and standalone RuntimeEngine are distinct; standalone gateway default constructor is not viable | One supported composition root per surface and explicit runtime adapter contract |
| W03 Memory/state/recovery | Optional core journal, HYPERSYNTH state and RuntimeEngine journal are distinct stores | Canonical StateCommit/RecoveryReceipt and cross-store recovery ownership |
| W04 Agent fabric | OperationalAgentFabric and other agent selection/coordination paths remain separate | AgentDescriptor, qualified identity, delegation lease, full DAG and result admission |
| W05 Routing/resources | Provider router/gateway/resilient executor are separate; resource selection not reservation | Single operation/effect coordinator and fenced PlacementLease |
| W06 NEXUS/FRL/evidence | Structural verifier, caller-fed evaluation and acquisition hash are separate evidence types | Claim/Evidence/SourceSpan graph and independent semantic/evaluation receipts |
| W07 MIRROR WORLD | Research/tool invocation authorization does not prove simulation provenance or reality bridge | WorldManifest, SimulationRun and separately authorized RealityBridgeApproval |
| W08 Surfaces/devices/browser/offline | /api/chat and /v1/execute have different ingress auth; client_id is metadata | SurfaceSession/DeviceAttestation and route-policy parity contract |
| W09 Security/crypto/audit/release | Secure boot, alerting, improvement and audit primitives are not all composed | TrustBundle, durable IncidentRecord and signed ReleaseEvidence |
| W10 Specialist domains | UIF route/domain label is not an independently qualified credential | DomainQualification with issuer, jurisdiction, scope and expiry |
| W11 Global operations | Local health/capacity abstractions are not durable fleet control or deployment proof | Attested nodes, leases/fencing, SLO/DR and release/deployment provenance |
| W12 Economy/governance/impact | High-risk payments capability registration is not a ledger/settlement/escrow/impact system | Segregated FinancialEntry ledger and independent ImpactEvidence |

## 9. Source traceability

The following blob SHAs identify the exact source files inspected at the stated branch snapshot:

| Path | Blob SHA |
|---|---|
| `web/app.py` | `a03d012d6f9f2fdbfb8a5e64397511e5ac692360` |
| `render.yaml` | `5d0b53c9578eb3d0cedc955cdee834faf31cb6ac` |
| `gateway/server.py` | `b434cdbe118ecea48029adcd2c954fa1ac14461c` |
| `gateway/runtime_adapter.py` | `6661fbc150c77ba79d3b1f16cc0f66742b20f935` |
| `gateway/auth.py` | `fa456172c99b183dcb2acd0ec99303ec540d2583` |
| `gateway/__main__.py` | `84a12211d50a3302ee5f0e9eb416ed03c00a243b` |
| `core/operational_runtime.py` | `0106879b43b8de90a87a11ca9c361be72ab37072` |
| `core/runtime.py` | `454f90e6b06ca6f013e325640a16d349b18797ae` |
| `core/hypersynth_runtime.py` | `8df911b42f558274e2e560be66846a2dba4c35e9` |
| `core/system_fabric.py` | `cf28bd8a144480467b6bd2cf3726b510a7b7924f` |
| `core/actions.py` | `5e2fc212abea2873bb471b12e6fe6f5021664e97` |
| `core/tools.py` | `a5c2797cce7c803abb272bab761b3288ba0f7e72` |
| `core/verification.py` | `ca80253776bd66a1c0ff4ef32f019c85bf510927` |
| `core/evaluation.py` | `df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e` |
| `core/frontier_capabilities.py` | `e76ace57c6d43b5db7d391ab533b0fa41ed5a6cc` |
| `core/secure_boot.py` | `32436ebc39f0044768e13340e8e6d1274cd5c51a` |
| `core/alerting.py` | `f8caee629f5c7e1ec0446c0a7d9c18f7cf3ac1b8` |
| `core/self_improvement.py` | `2cc85de48becd7243e6d3d572dded25841587a08` |
| `core/provider_router.py` | `9bd085ddaf660ac53039dd80eb6c822cb9226eba` |
| `core/provider_execution.py` | `93e63c085321e2b4413dbcf4878a4c4f6a82953e` |
| `core/provider_resilience.py` | `a678329d5b29a184a7b26ca9bc71ff0a232df136` |
| `noryx7_runtime/engine.py` | `128e0522cb2234e115ae2b2e770279374a633a4d` |
| `noryx7_runtime/state.py` | `444aba1fb92a4bb70ee2ee31b23d3946680bb630` |
| `noryx7_runtime/model_fabric.py` | `abb8bd9bb3217fff967e898afbdc491eb5082f45` |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` |

## 10. New gap records and disposition

- `GAP-HTTP-INGRESS-PRINCIPAL-AND-POLICY-PARITY`: align direct and session-protected routes; resolve client labels to principals and enforce audience/scope/device/policy epoch.
- `GAP-COMPOSITION-ROOT-AND-EXECUTION-PLANE-OWNERSHIP`: declare supported production composition roots and map HYPERSYNTH, RuntimeEngine and CanonicalSystemFabric without implicit authority duplication.
- `GAP-STANDALONE-GATEWAY-BOOTSTRAP-INJECTION`: make the standalone gateway entry point inject a valid model fabric/runtime or explicitly remove unsupported startup mode.
- `GAP-CROSS-PLANE-PROVIDER-EFFECT-COORDINATION`: unify operation identity, retries, idempotency and uncertain-effect reconciliation across provider paths.
- `GAP-ASSURANCE-COMPONENT-COMPOSITION-AND-DELIVERY`: bind boot, alerting, self-improvement and global operations to actual consumers, durable evidence and delivery/rollback acknowledgements.

These records are architecture closure requirements, not exploitability claims. Existing decisions remain OPEN unless their designated ADR owner explicitly accepts them. W01–W12 remain PARTIAL. No source implementation, integration, test campaign, merge, deployment or freeze is claimed.
