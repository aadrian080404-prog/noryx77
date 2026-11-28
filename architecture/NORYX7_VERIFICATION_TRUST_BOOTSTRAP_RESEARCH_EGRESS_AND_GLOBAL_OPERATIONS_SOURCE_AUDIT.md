# NORYX7 — Verification, Trust Bootstrap, Research Egress and Global Operations Source Audit

**Review date:** 2026-11-25  
**Source revision:** `6231e7caaccedfdea5c8a4e6f73aef0f4e5129af`  
**Scope:** W05/W06/W07/W09/W10/W11, with W01/W02/W03/W08/W12 handoffs.  
**Mode:** architecture-only source audit. No implementation, tests, workflow, dependency, configuration, deployment or runtime changes.

## 1. Executive findings

This pass inspects concrete source behavior behind verification, evaluation, specialist routing, web research, secure boot, observability/alerting, self-improvement and global operations. It distinguishes bounded local controls from the stronger end-to-end properties required by the canonical handoff catalog.

| Area | Observed source behavior | Not established by this source scope |
|---|---|---|
| Result verification | `core/verification.py` validates task shape, selected risk labels, result count/order/agent/task/execution IDs, completed status, a prior valid marker and non-empty output. | Semantic correctness, independent evidence validation, evaluator independence, provenance truth, calibration, domain qualification or claim entailment. |
| Evaluation | `core/evaluation.py` aggregates caller-supplied pass flags, scores and non-empty evidence strings; all recorded dimensions must pass. | Evidence artifact verification, independent evaluator identity, campaign execution, holdout isolation or reproducible score derivation. |
| Specialist fabric | `core/universal_intelligence.py` routes using bounded keyword matching over task fields and emits evidence-bearing assessment structures. | Competence credential, jurisdiction/scope, independent specialist execution, source custody or verified professional authority. |
| Secure boot | `core/secure_boot.py` accepts a caller-supplied expected digest equality per stage, appends stage names and computes a hash during admission. | Anchor-to-measurement cryptographic chain, required stage ordering/completeness, signer verification, anti-rollback, hardware root or policy-bound admission. |
| Web research | `core/frontier_capabilities.py` fetches HTTPS URLs with TLS context, timeout and response byte cap, and parses result links. | Destination allowlist, resolved-IP/private-network denial, redirect revalidation, DNS rebinding protection, provenance authority, content sanitization or claim entailment within this module. |
| Security observation | `core/observability.py` holds a bounded in-memory event list; `core/alerting.py` creates in-memory verified-alert records and declares delivery adapters external. | Durable tamper-evident audit, delivery confirmation, incident orchestration, on-call acknowledgement or recovery evidence. |
| Self-improvement | `core/self_improvement.py` enforces a local stage order and an external admission method after VERIFY. | Proposal/patch digest binding to tested artifact, independent verifier identity, signed approval, release provenance, canary evidence or rollback authority. |
| Global operations | `ecosystem/global_fabric.py` and `ecosystem/global_scale.py` model bounded in-process registries, memory metadata, health, capacity selection, metrics and staged self-healing. | Durable control plane, actual distributed replication, capacity reservation/fencing, node attestation, quorum, service SLO/DR evidence or real deployment orchestration. |

These findings are bounded to inspected source files and revision. They do not prove that external infrastructure or upstream controls do not exist.

## 2. W06 — Verification and evaluation boundary

### 2.1 Result verification

In `core/verification.py`:
- `verify_task` validates TaskSpec shape and a fixed risk vocabulary.
- `verify_output` rejects null/empty output; non-empty content is otherwise admitted at this stage.
- `verify_agent_results` checks expected agent ID, execution ID, ordered task IDs, result count, completed status, a well-formed prior VerificationResult with `valid=True`, and output presence.
- `verify_state` checks status/verdict membership.

This is useful structural and lineage checking. It is not a semantic verifier: the prior verification marker is a data object supplied on the result and the engine does not independently recompute the underlying claim or validate attached source evidence.

**Required contract:** ResultAdmission must identify evaluator, policy/schema version, task coverage, exact source/evidence artifacts, semantic method, independence class, uncertainty and verdict scope. A structural pass must not be represented as factual correctness.

### 2.2 Evaluation matrix

In `core/evaluation.py`, `EvaluationMatrix.record` accepts a typed dimension, caller-supplied boolean, finite score in [0,1] and non-empty evidence string. `passed()` requires at least one result and every result to pass.

This correctly prevents one recorded failed dimension from being hidden by averaging. However, the matrix itself does not validate evidence authenticity, derive the score, bind the evaluator to a build/configuration, or prove independence.

**Required contract:** each evaluation item binds case ID, immutable input/expected criteria, evaluator identity/version, run environment, raw output, evidence digest, score derivation and independent review where required. Campaign manifest creation is distinct from execution and holdout proof.

## 3. W09 — Secure boot and trust bootstrap

### 3.1 Source-level observation

In `core/secure_boot.py`:
- TrustAnchor validates a non-empty ID and digest length, but not digest alphabet/algorithm or signature.
- `verify_stage` accepts any non-empty stage name and two caller-provided strings whose equality and digest length match; it appends the stage name.
- There is no required stage manifest or ordering check.
- `admit` hashes the accumulated stage-name string with the supplied system digest, then returns true if at least one stage exists and the derived hash is not all zeroes.
- The configured `anchor.digest` is not consumed by `verify_stage` or `admit`.

The admission predicate therefore does not establish that the system digest chains to the configured trust anchor or that required boot stages were measured and signed. This is a concrete mismatch between the class's secure-boot-style name/docstring and the guarantees visible in this implementation. It is not evidence that this class is currently wired as the production boot authority.

### 3.2 Required trust-bootstrap contract

A future implementation must define:
1. immutable signed trust-root manifest and permitted signer roles;
2. exact ordered stage manifest, stage identity and measured artifact digests;
3. cryptographic verification using pinned root/key epoch, not caller-supplied equality alone;
4. binding of each stage to predecessor digest, platform/device identity and boot nonce;
5. anti-rollback version/counter and revocation semantics;
6. measured boot source and hardware/OS trust assumptions;
7. failure states, recovery authorization and independent audit;
8. integration proof showing every privileged runtime admission consumes this verified result.

No secure-boot production guarantee is claimed by the current source.

## 4. W05/W09 — Research acquisition and egress boundary

### 4.1 Source-level observation

In `core/frontier_capabilities.py`, WebResearchCapability:
- accepts an explicit URL or target URL;
- requires HTTPS and a non-empty network location;
- uses the default TLS validation context;
- sets a timeout and reads at most max_bytes + 1;
- returns the final response URL/status/content type/body;
- parses result links and attempts to fetch up to ten HTTPS links.

The inspected capability does not itself implement hostname allowlisting, IP-range denial, DNS pinning/rebinding defense, redirect destination revalidation, response content isolation or publisher-authority validation. Python's URL opener can follow redirects; the code shown does not add a per-hop policy check.

This does not prove that an upstream tool authorization or network egress layer is absent. The security question is whether those controls are enforced at the actual socket/redirect boundary and cannot be bypassed by another caller.

### 4.2 Required acquisition/effect contract

- Separate search-provider endpoints from user-supplied source URLs.
- Normalize and validate scheme, hostname, port, userinfo and IDNA representation.
- Resolve and reject loopback, link-local, private, multicast, reserved and metadata-service destinations for every connection.
- Revalidate each redirect hop and bind the connected peer to the approved resolution; account for DNS rebinding.
- Enforce byte, decompression, redirect, time, content-type and concurrency limits.
- Keep fetched bytes, final URL, redirect chain, response headers, retrieval time and digest as a SourceArtifact with exact SourceSpan extraction lineage.
- Treat fetched text as untrusted data, never as executable instruction or verified claim.
- Verify publisher identity/signature independently where the source type supports it.
- Prove all network access crosses the same enforceable egress policy.

## 5. W09 — Observability, alerting and incident lifecycle

`core/observability.py` uses a bounded in-process event list with local sequential integer IDs and wall-clock timestamps. It raises on capacity exhaustion; it does not persist or sign events.

`core/alerting.py` queues verified alert objects in memory. Its policy can list PHONE/COMPUTER/EMERGENCY_CALL channels, but delivery adapters are external and no delivery/acknowledgement is performed by AlertRouter.

Required distinction:
- detected event;
- integrity-validated event;
- policy-classified alert;
- delivery attempt;
- delivery acknowledgement;
- human acknowledgement;
- containment authorization;
- recovery and post-incident closure.

The architecture must not treat an alert object or channel label as a delivered notification. Define durable event sequencing, signed checkpoints, retention, dropped-event detection, tenant-safe access, delivery retries/idempotency, acknowledgement escalation, and incident evidence retention.

## 6. W11 — Global operations and capacity

`ecosystem/global_fabric.py`:
- stores memory records as digest/provenance metadata plus a declared replica tuple; it does not transport or persist payload bytes;
- holds identity/session/device/capability metadata in a local dictionary;
- checks a policy digest and capability string on lookup, but does not itself establish signed issuer, freshness, expiry, revocation epoch or external identity proof.

`ecosystem/global_scale.py`:
- models regions/cells and health/capacity in process;
- selects a healthy region/cell from the current registry snapshot;
- includes degradation modes, bounded metric buffers, disaster-recovery target selection and a staged self-healing state controller;
- does not itself reserve/decrement capacity across concurrent workloads, issue fenced expiring leases, replicate control-plane state, execute deployment or prove restore/failover.

**Required global operations contract:** durable membership and node identity; attested health; atomic capacity reservation with expiry/fencing; placement and data-residency policy; quorum/replication semantics; control-plane split-brain handling; SLO/error budgets; incident ownership; backup/restore; regional failover; release provenance and rollback; energy/cost/fairness measurement.

## 7. W10/W12 — Qualification, self-improvement and impact separation

The specialist routing and assessment structures in `core/universal_intelligence.py` are cognitive routing/proposal primitives, not credential verification. Domain qualification must be independently issued, scoped, jurisdiction-bound, time-limited, revocable and conflict-aware.

`core/self_improvement.py` advances a local stage enum and allows `admit_external` once VERIFY is reached. The method does not itself accept a verifier receipt, signed approval, tested artifact digest, deployment target, canary evidence or rollback proof. Its name is therefore a workflow model, not an autonomous safe deployment system.

W12 impact claims must remain separate from code self-improvement and operational metrics. Activity counts, generated scenarios, simulated estimates and financial entries are not independently measured net environmental/social outcomes.

## 8. New gaps and closure evidence

| Gap | Streams | Required closure evidence |
|---|---|---|
| GAP-SEMANTIC-RESULT-ADMISSION | W02/W04/W06/W10 | Independent semantic evaluator, source-bound claims, scope/uncertainty, calibration and evaluator identity. |
| GAP-EVALUATION-EVIDENCE-ATTESTATION | W06/W09/W11 | Bind each score/pass to immutable case, build, evaluator, raw output and reproducible evidence; prove holdout isolation. |
| GAP-SECURE-BOOT-ANCHOR-CHAIN | W01/W09/W11 | Cryptographically chain ordered measured stages to configured root; validate signatures, anti-rollback and runtime admission consumer. |
| GAP-RESEARCH-URL-EGRESS-ENFORCEMENT | W05/W06/W08/W09/W11 | Prove DNS/IP/redirect validation and network-level egress policy for every acquisition path; bind bytes and spans to custody records. |
| GAP-OBSERVABILITY-DURABLE-INCIDENT-CHAIN | W03/W09/W11 | Durable signed event chain, gap detection, delivery acknowledgements, incident ownership and recovery evidence. |
| GAP-GLOBAL-CAPACITY-LEASE-AND-FENCING | W05/W08/W11 | Atomic expiring reservations, node attestation, fencing, split-brain and failover evidence. |
| GAP-SELF-IMPROVEMENT-RELEASE-ATTESTATION | W06/W09/W11 | Bind proposal to exact tested artifact, independent verification, signed approval, canary, deployment measurement and rollback. |
| GAP-SPECIALIST-CREDENTIAL-VERIFICATION | W01/W06/W10 | Issuer-verified scoped credentials, jurisdiction, expiry, conflict and independent review. |

All gaps are architecture closure requirements. They do not establish that an exploit exists or that external controls are absent.

## 9. Parallel stream impact

- **W01:** bind trust roots, principal assertions and revocation epochs to measured runtime admission.
- **W02:** ensure semantic admission and effect certainty gate final operation state.
- **W03:** persist audit/incident/evaluation evidence and distinguish commit from observation.
- **W04:** bind specialist/agent delegation to qualification and evaluator independence.
- **W05:** enforce destination and capacity policies at actual provider/network boundaries.
- **W06:** upgrade from structural output checks to typed claim/evidence admission and reproducible evaluation.
- **W07:** keep simulated, acquired and observed world state epistemically distinct.
- **W08:** require all surface/browser/offline acquisition to inherit the same egress and trust rules.
- **W09:** close boot trust, key custody, signed audit and incident/release assurance.
- **W10:** make specialist authority scoped and credential-backed.
- **W11:** move from local capacity models to durable reservations, attested fleet and operational recovery.
- **W12:** ensure no operational metric or simulation score is misrepresented as independently measured public impact.

## 10. Disposition

This audit adds source-grounded constraints and gaps; it does not implement fixes, approve ADRs or certify runtime behavior. The exact inspected source revision is recorded above. Follow-up source changes require re-audit of affected call sites and evidence cards.

**W01–W12 remain PARTIAL. Architecture remains unfrozen.**
