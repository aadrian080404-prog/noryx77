# NORYX7 — Cognitive Pipeline, Research Acquisition, Global Fabric and Trust/Egress Assurance Reconciliation

**Date:** 2026-11-25  
**Repository:** `aadrian080404-prog/noryx77`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Inspected source HEAD:** `773cd0186e58a8df0f399dbd01157f49a665684c`  
**Mode:** architecture-only, bounded source reconciliation  
**Disposition:** W01–W12 remain PARTIAL.

This pass joins cognitive hypothesis/simulation, metacognitive challenge, web research acquisition, global memory/capacity abstractions, egress policy, trust chain and evaluation campaign. It does not certify production deployment, dynamic call reachability, independent scientific truth or global distributed behavior. No runtime/test/workflow/configuration file is changed.

## 1. Exact source anchors

| Source | Blob SHA | Bounded observation |
|---|---|---|
| `core/reasoning.py` | `7bf5d905f07b4805e3505e13408a685d81f7842b` | Hypotheses mirror plan objectives; InternalSimulator checks declared-plan consistency and non-empty statements, not an external/world model. |
| `core/metacognition.py` | `9aed7b2522175f6e4a097631566682cdff6a118f` | Final pipeline reflection checks structure and delegates a challenge check; confidence is a fraction of boolean checks. |
| `core/metacognitive_challenge.py` | `3f343b153b971559a72730dcfcbb8412f8879d74` | Injected independent challenge verifier exists; default PipelineChallengeVerifier checks pipeline shape, IDs, ordering and output consistency. |
| `core/frontier_capabilities.py` | `e76ace57c6d43b5db7d391ab533b0fa41ed5a6cc` | Web research fetches HTTPS URLs and emits content hashes; no egress-policy injection is visible in this capability. |
| `core/egress.py` | `e50095f8a0265adfcac4812aa06778cece58fe83` | Explicit in-memory component/host/port/protocol allow-list primitive. |
| `core/trust_chain.py` | `bac239a5a5e451a69a89c6456daecf34fe344e48` | Composes agent identity, device trust, attestation digest, secure-channel binding, epoch, action digest, signature and replay guard. |
| `ecosystem/global_fabric.py` | `d0f10d09cc739616f88f3e24966e3302e4aadb30` | Global memory index stores payload/provenance digests and replica IDs in a local bounded map. |
| `ecosystem/global_scale.py` | `7393cda34d4b57e2310d20cafccc0489a1ab813e` | Region/cell capacity selection and elastic compute reservation abstractions; EventFabric is explicitly in-memory. |
| `core/evaluation.py` | `df35992d09ffb2a9a82e0c1c739b4de3f1b7dd4e` | Evaluation matrix stores supplied dimension/result/evidence strings. |
| `core/evaluation_campaign.py` | `44db107096abf02f0cde62ba0393f87eda465753` | Deterministic case/holdout manifest generation; cases are generated but not executed by this layer; record accepts externally produced evidence. |
| `core/cyber_range.py` | `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be` | Synthetic sandbox-only cyber simulation with owner authorization. |
| `core/secure_boot.py` | `32436ebc39f0044768e13340e8e6d1274cd5c51a` | Digest-comparison secure-boot-style chain primitive. |

## 2. Cognitive reasoning and simulation: structural consistency is not world validity

### Observed
- `HypothesisEngine` converts each plan step objective into a hypothesis with that step ID as its basis.
- `HypothesisEngine.verify` validates identity, uniqueness and non-empty structure.
- `InternalSimulator.simulate` marks a hypothesis feasible when its statement is non-empty and its task ID matches. Its own docstring describes a bounded pre-execution check over the declared plan.
- `InternalSimulator.verify` checks result shape, uniqueness and feasibility flags.
- `CrossChecker` checks one-to-one result/step mapping, completion, non-null output, execution identity and verification stage.
- `MetacognitionEngine` validates plan/hypothesis/simulation/result correspondence and calculates confidence as the fraction of boolean checks that pass.
- `PipelineChallengeVerifier` is independent of the primary verifier in call path, but the inspected implementation checks pipeline shape, identity, ordering, completion and final-output consistency. It does not independently prove domain facts or compare the output against external ground truth.

### Architecture requirement
Split the term "simulation" into explicit tiers:
1. **Plan consistency check** — structural validity of plan/hypothesis mapping.
2. **Deterministic execution model** — defined state-transition model with versioned semantics.
3. **Domain simulation** — physical, ecological, economic, cyber or social model with declared assumptions and validated parameters.
4. **Digital twin / observed system** — synchronized measurements and model residuals.
5. **Forecast** — calibrated probabilistic claim over a defined target and horizon.

Each result must identify its tier. Never promote a plan-consistency check into evidence that an operation is physically feasible. A semantic verifier must have an independently sourced oracle or evidence set, and report its scope and uncertainty. Metacognitive confidence must be calibrated against actual outcomes, not only the fraction of internal boolean checks.

## 3. Challenge evaluation and independent verification

### Observed
- `IndependentChallengeVerifier` accepts an injected verifier callback and records whether it returned exactly True, alongside answer-digest equality.
- `MetacognitiveChallengeEvaluator` derives scores from the challenge verification and trace fields.
- `PipelineChallengeVerifier` is a separate structural challenge path but does not independently re-derive the correctness of the task answer.
- `EvaluationCampaign` creates reproducible generated cases and holdout assignment; it does not execute those cases or independently inspect the truth of evidence supplied to `record`.
- `EvaluationMatrix` requires evidence strings and checks dimensions/pass flags; the evidence provenance and verifier independence are external to the matrix.

### Architecture requirement
A campaign must bind immutable dataset/version, case generator, seed, split policy, evaluator identity, execution artifact, raw result, scoring rubric and holdout access log. Enforce holdout isolation technically, not by convention. Independent verification needs a distinct trust domain, blind evaluation where appropriate, and auditable proof that the primary agent could not write or alter the oracle. Scores must expose sample size, confidence interval, subgroup coverage, leakage checks and evaluator disagreement.

## 4. NEXUS research acquisition and evidence provenance

### Observed
- `WebResearchCapability` can fetch a caller-supplied HTTPS URL or a configured search-template URL, parse result links, fetch up to ten sources and emit URL, title, snippet, content hash, status and content type.
- The output content hash binds the returned body bytes as decoded/re-encoded by this path; it does not by itself prove publisher identity, publication date, author, source authority, completeness, or that the snippet supports a downstream claim.
- The inspected capability uses `urlopen` directly. The separate `EgressPolicy` class is an allow-list primitive, but this source does not show it injected into WebResearchCapability. This is a call-path/integration question, not a confirmed vulnerability; deployment network controls may exist outside the inspected file.
- The capability fetches arbitrary supplied HTTPS destinations at this layer; redirects and DNS/IP destination policy need explicit treatment in a production acquisition boundary.

### Architecture requirement
Define a SourceAcquisitionGateway with canonical URL parsing, host allow-list/deny-list, redirect revalidation, DNS/IP and private-network restrictions, TLS policy, byte/time limits, content-type policy, robots/terms/consent rules, immutable raw artifact custody and acquisition timestamp. Preserve original bytes and encoding rather than relying only on normalized text. Evidence records must distinguish source artifact from extracted span, claim, model-generated summary and reviewer judgment. Track author/publisher, authority scope, publication/modified/access times, locale, version, rights, transformation lineage and retraction/correction status.

NEXUS/FRL must connect each ClaimRecord to exact EvidenceRecord spans and typed relations (supports, contradicts, qualifies, supersedes, derived-from). Source diversity must not be mistaken for independence when sources share ownership, syndication, upstream wire or model lineage.

## 5. Global fabric and resource placement: reservation abstractions versus distributed guarantees

### Observed
- `GlobalMemoryFabric` records payload/provenance digests, level, version and a tuple of replica IDs. The implementation stores record metadata in a bounded local dictionary; the replica tuple is not a replication acknowledgement.
- `GlobalIdentityAuthorizationFabric` is a local authorization index; it does not prove globally consistent revocation.
- `GlobalControlPlane` and `CellRegistry` select region/cell by residency, health and declared capacity.
- `ElasticComputeFabric.acquire` subtracts capacity from a local worker-pool map and `release` returns it. This is a local reservation abstraction, not a cross-region lease/fencing protocol.
- `EventFabric` explicitly documents a bounded in-memory queue; durable brokers belong behind adapters.

### Architecture requirement
For global operations define node identity/attestation, registry consensus scope, health lease expiry, capacity reservation token, fencing epoch, placement constraints, data residency, encryption/key custody, replication acknowledgements, quorum/consistency model, version vectors, conflict resolution, durable event offsets and recovery. A list of replicas must be replaced by per-replica signed write acknowledgements and verifiable read/recovery state. Capacity must be tied to an expiring lease and atomically reserved at the actual worker, not only a planning snapshot.

## 6. Trust chain and egress policy: meaningful controls, integration still to prove

### Observed
- `TrustChain` binds agent identity, verified device identity, agent attestation digest, secure-channel session/direction, execution epoch and action digest in a signed Ed25519 evidence object.
- Verification checks trusted agent identity, attestation, expected device/peer/session/direction, epoch and optional replay consumption.
- It can additionally require the live `DeviceCapabilityGate` to authorize the exact capability at the expected epoch.
- Its default `AuthorizationReplayGuard` is constructed inside the TrustChain instance unless injected; distributed replay consistency and persistence are not established by this module.
- `EgressPolicy` is a bounded in-memory allow-list keyed by component, canonicalized host, port and protocol.
- Presence of a policy object does not prove all outbound sockets, provider adapters, browser WebViews and research fetches are forced through it.
- `SecureBootChain` compares declared stage digests against expected digests; the module alone does not establish a hardware root, measured boot evidence source, anti-rollback counter or runtime enforcement.

### Architecture requirement
Create an enforceable EgressControlPlane with mandatory transport adapters, default-deny network namespace/firewall controls, DNS rebinding/redirect protections, policy epoch, revocation and auditable denied/allowed events. Demonstrate coverage for HTTP clients, model providers, browser processes, device adapters, sync channels and update services. TrustChain evidence should be required at the actual action boundary and bound to a durable replay store/fencing epoch. Secure boot must consume measured evidence from a platform root and be linked to runtime attestation and signed release provenance.

## 7. W01–W12 impact

| Workstream | New clarification | Remaining closure evidence |
|---|---|---|
| W01 Identity | TrustChain composes multiple local trust proofs; replay guard scope is instance-dependent. | Shared issuer/registry, durable replay, revocation and cross-node fencing. |
| W02 Runtime | Cognitive pipeline checks structure and internal feasibility, not general world truth. | Typed execution/simulation tier and evidence-backed semantic verification. |
| W03 Memory | Global memory records replica identifiers and digests in a local index. | Durable payload custody, replica acknowledgements, quorum and recovery. |
| W04 Agent Fabric | Metacognitive pipeline can challenge structural consistency. | Independent domain oracles, qualification and non-self-certified results. |
| W05 Routing | Region/cell/compute selection uses declared local capacity. | Real reservations, leases, fencing and placement evidence. |
| W06 NEXUS | Research acquisition returns hashes/snippets, not complete source-to-claim provenance. | Immutable source artifacts, exact spans, authority, transformations and contradiction graph. |
| W07 MIRROR WORLD | InternalSimulator is a plan consistency check; cyber range is synthetic sandbox simulation. | Domain-specific models, calibration, real observations and sim-to-real validation. |
| W08 Interfaces | Egress allow-list exists as a primitive. | Mandatory enforcement across every network-capable surface. |
| W09 Security | TrustChain and secure-boot-style digest checks exist. | Durable replay, hardware root, measured boot, release linkage and revocation. |
| W10 Specialist Domains | Challenge domains and scores are represented. | Independently validated benchmark suites and domain qualification. |
| W11 Operations | Evaluation manifests are reproducible, but campaign execution/evidence production is external. | Holdout isolation, immutable runs, independent evaluator and release binding. |
| W12 Ecosystem | Global capacity and evidence primitives do not establish financial or environmental outcome truth. | Ledger controls and independent baseline/counterfactual impact verification. |

## 8. Architecture decisions to reconcile (reuse existing ADRs)

- Distinguish structural plan checking from simulation and domain validation.
- Independent verifier/oracle ownership and holdout isolation.
- NEXUS source acquisition, URL/egress policy and immutable evidence custody.
- Global replica acknowledgement, consistency and recovery.
- Capacity leases, fencing and placement reservations.
- TrustChain replay persistence and mandatory egress enforcement.
- Secure boot root, measured boot and release attestation linkage.

Do not infer new ADR identifiers. Reconcile with the current Architecture Decisions Backlog.

## 9. Closure gates

- Every network-capable component is proven to traverse an enforced egress boundary.
- Every simulation result declares its fidelity tier and is validated against independent observations appropriate to its domain.
- Every research claim resolves to immutable source bytes and exact supporting/contradicting spans.
- Every independent evaluator has a distinct trust identity and protected oracle/holdout boundary.
- Every global memory replica and capacity reservation has an actual signed acknowledgement/lease, not only a local identifier.
- Trust-chain replay and revocation behavior is durable and bounded across the intended deployment scope.
- All findings are tied to immutable source revisions and exact verification scope.

**Disposition:** W01–W12 remain PARTIAL. Architecture-only; no integration, test modification, workflow change, merge or deployment is authorized by this pass.
