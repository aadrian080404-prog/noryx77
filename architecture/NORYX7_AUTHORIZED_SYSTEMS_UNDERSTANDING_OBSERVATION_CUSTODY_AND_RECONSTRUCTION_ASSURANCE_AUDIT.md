# NORYX7 — Authorized Systems Understanding, Observation Custody and Reconstruction Assurance Audit

**Review date:** 2026-11-27  
**Source-tree HEAD inspected:** `badb8f12e6d45d6a497d938f45ab130a044bbd19`  
**Branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Mode:** architecture-only source audit and cross-stream contract proposal. No runtime, browser, test, dependency, workflow, deployment, frozen baseline or production configuration changed.

## 1. Executive finding

NORYX7 has a useful safety boundary for its current cyber range: synthetic targets are constrained to the `sandbox` trust zone and actions are symbolic. It also has stronger cryptographic identity and action-authorization primitives elsewhere in the source tree. These mechanisms are not yet one end-to-end authorization, observation-custody, reconstruction and evidence-admission lifecycle.

The current cyber-range authorization is a small record containing principal ID, authorization ID and expiry. It is not cryptographically signed, target-bound, operation-bound, scope-bound, revocable through a live authority, or linked to a captured observation. The simulation report sets `verified=True` after constructing symbolic actions; this is a report flag, not proof that an external system was observed, that a reconstruction matches it, or that a vulnerability exists.

NORYX7's intended Systems Understanding / Reverse Engineering capability therefore needs a clear distinction between:
1. permitted observation of a system;
2. reconstruction/inference from observations;
3. controlled simulation of a candidate model;
4. independent verification of a claim;
5. any separately authorized real-world test or actuation.

A simulation, model, protocol hypothesis, generated test or successful parser must never imply permission to probe a real system.

## 2. Bounded source observations

### 2.1 Cyber range — `core/cyber_range.py`

Blob SHA: `2896f5b5fc95d7e2653d380fa40c4f0dc772e4be`.

Observed:
- `SyntheticTarget` rejects any `trust_zone` other than `sandbox`; the target has a caller-supplied ID and vulnerability strings.
- `OwnerAuthorization` contains `principal_id`, `authorization_id`, `expires_at`; `valid_for` checks matching principal, `now <= expires_at` and a non-empty authorization ID.
- No signature, issuer, target ID, asset ownership proof, permitted operation set, scope, not-before, policy epoch, nonce/replay control, revocation lookup or immutable authorization evidence is represented in this record.
- `CyberRange.simulate` accepts a caller-provided principal ID, authorization object, time and technique strings. It verifies the local sandbox target exists and generates symbolic actions.
- `SimulationReport.verified` is returned as `True` after constructing the symbolic sequence; no independent validator, observed system, expected behavior oracle or evidence-backed result is evaluated.

This is appropriate as a bounded synthetic exercise primitive, but it is not a real-system authorization service or empirical vulnerability verification engine.

### 2.2 Existing test evidence — `core/test_cyber_range.py`

Blob SHA: `3d13abfe6ea0a48ba23d526e55cf41a212b2acc5`.

Tests cover:
- mismatched principal rejection;
- expired authorization rejection;
- rejection of a target whose trust zone is not `sandbox`;
- symbolic action generation and the report's `verified=True` flag.

The tests do not establish signed or revocable owner authority, target ownership, scope/operation binding, capture provenance, observation integrity, reconstruction fidelity, independent vulnerability verification or real-target safety. Tests were inspected, not run in this pass.

### 2.3 Stronger but separate primitives

- `core/identity.py` (blob SHA `e6e8e5b03135251baca489643f86c7d81a755a08`) defines Ed25519-backed agent identities/attestations and an explicit in-memory trust registry with revocation. Agent identity is not automatically a human/organization asset-owner identity or an authorization to observe a target.
- `core/actions.py` (blob SHA `5e2fc212abea2873bb471b12e6fe6f5021664e97`) defines an HMAC-backed one-shot authorization grant bound to action fingerprint, execution, principal key fingerprint, nonce and expiry. It is a useful action gate primitive, but its existence does not prove that the cyber-range path uses it or that a target's owner has delegated the specific observation scope.
- `core/reasoning.py` (blob SHA `7bf5d905f07b4805e3505e13408a685d81f7842b`) maps each plan step to one hypothesis and performs structural feasibility checks; it does not reconstruct a system from captured traces or test semantic equivalence.
- `core/verification.py` (blob SHA `ca80253776bd66a1c0ff4ef32f019c85bf510927`) checks output presence and task/result structure; it does not prove a system-model claim is entailed by observations.
- `core/evaluation_campaign.py` (blob SHA `44db107096abf02f0cde62ba0393f87eda465753`) generates deterministic local cases and holdout manifests; it does not execute them or independently attest externally supplied pass/score/evidence.

These components should be composed through explicit typed contracts, not treated as interchangeable evidence or authority.

## 3. Canonical Systems Understanding lifecycle

Proposed sequence:

`SCOPE_REQUESTED → OWNER_AND_PRINCIPAL_AUTHENTICATED → AUTHORIZATION_GRANTED → OBSERVATION_CAPTURED → CUSTODY_SEALED → NORMALIZED_WITH_LINEAGE → RECONSTRUCTION_BUILT → CLAIMS_GENERATED → INDEPENDENTLY_CHECKED → ACCEPTED_FOR_DECLARED_SCOPE`

Alternative terminal/intermediate states:
- `DENIED`: no valid asset-owner authority or prohibited scope.
- `EXPIRED` / `REVOKED`: observation authority no longer valid.
- `QUARANTINED`: capture integrity, provenance or parser safety is uncertain.
- `INCOMPLETE`: missing coverage or unobserved behavior prevents a conclusion.
- `CONTRADICTED`: new observations falsify or materially weaken a reconstruction.
- `OUT_OF_SCOPE`: requested conclusion exceeds the authorized asset, interface, time or method.
- `REQUIRES_HUMAN_REVIEW`: high-impact or ambiguous conclusion cannot be auto-admitted.

This is a lifecycle of evidence and authority, not a generic task status. A rejected or expired authorization cannot be revived by reusing an old capture or model.

## 4. Proposed typed contracts

### 4.1 SystemScopeAuthorization

Must bind:
- authorization ID/version, issuer, signature and trust chain;
- authenticated owner/controller legal identity and evidence of control over the asset/interface;
- requesting principal, organization/tenant and enrolled device/workload;
- exact target asset IDs, hostnames, endpoints, software build or physical asset identity;
- allowed interfaces and observation methods (e.g. owner-provided documentation, exported logs, passive packet capture, test environment);
- explicitly allowed active test classes, if any, with strict rate/concurrency/time/impact bounds;
- prohibited actions, excluded data classes and safety constraints;
- geographic/jurisdictional scope, purpose and retention/use rights;
- validity interval, revocation sequence, nonce, policy epoch and audit correlation;
- whether third-party dependencies and subcontracted infrastructure are excluded.

Authorization must be least-privilege. A permission to inspect a supplied binary does not authorize network probing of its vendor. Permission to capture traffic on one test VLAN does not authorize scanning other networks. Ownership of one domain does not automatically authorize testing its cloud provider, users or integrated third-party services.

### 4.2 ObservationCaptureManifest

Every capture binds:
- capture ID, exact asset/interface, observer identity and active authorization ID;
- capture method, tool and version, configuration, clock source and time interval;
- original byte/object digest, content type, size and encoding;
- source endpoint and direction where applicable, packet/session boundaries and loss counters;
- redaction/transformation chain with both original and derived digests where retention is lawful;
- secret/credential/PII detection and quarantine decision;
- collection consent, rights, retention expiry and permitted downstream use;
- tamper-evident signature and storage custody events.

A digest establishes integrity of the captured bytes relative to the digest; it does not establish that the source was authentic, the observer was authorized, or the capture is complete.

### 4.3 ReconstructionModel and BehaviorClaim

A reconstruction model binds:
- source capture manifest IDs and exact evidence spans;
- model/schema version, parser/decompiler/dissector/tool versions and configuration;
- inferred components, interfaces, state variables, transitions, dependencies and trust boundaries;
- observed behavior versus inferred behavior versus unknown behavior;
- assumptions, alternative explanations, missing coverage and confidence semantics;
- protocol grammar/state machine, error behavior, timing and version applicability;
- claim IDs, support/contradiction edges and provenance lineage;
- prohibited inference boundaries (e.g. do not infer secrets, private source or unobserved internals from a black-box response alone).

Each claim must be scoped: what exact asset/version, interface, traffic conditions and observation period does it describe? A protocol model that explains a sample trace is not proof it describes all protocol states.

### 4.4 ReconstructionVerificationReceipt

A verifier receipt binds:
- claim/model digest and declared validity scope;
- independent verifier identity, qualification, tools and version;
- held-out observation set or independently generated test oracle;
- positive, negative and boundary test results;
- counterexamples, unexplained traces, coverage and known blind spots;
- reproduction instructions, environment and deterministic seeds where relevant;
- acceptance verdict and expiry/revalidation trigger.

The verifier must not simply repeat the same extraction pipeline, source corpus, prompt or model and then be counted as independent. Independence profile and common failure domains must be declared.

## 5. Separate observation, simulation, verification and active testing

| Plane | Permitted evidence | What it cannot claim |
|---|---|---|
| Passive observation | Owner-authorized logs, traces, captures, documentation, sensor readings | Complete system knowledge or permission to send probes |
| Reconstruction | Versioned hypotheses and models derived from captured evidence | That inferred internals are observed facts |
| Synthetic simulation | Symbolic actions, synthetic assets, deterministic scenarios | Real-world exploitability, target ownership or production behavior |
| Controlled test environment | Results from an explicitly scoped owner-controlled lab/staging system | Permission to test production or adjacent infrastructure |
| Real-system active test | Only the exact operations in a valid signed asset-owner authorization | Blanket permission for other targets, methods or time windows |
| Reality Bridge actuation | Separate operator approval, device identity, interlocks and bounded command receipt | Authority inherited from a model, simulation or research agent |

The safe default is passive analysis of user-provided or owner-authorized artifacts. Active network interaction is a separate high-risk capability and should remain disabled unless a dedicated authorization and operational safety review pass.

## 6. NEXUS / FRL evidence admission

NEXUS should store source artifacts, claims, observations, inferred models, formal propositions and disputed claims as distinct typed nodes. FRL should verify formal proof artifacts against a declared checker/theory/version and exact proposition.

Required admission rules:
- no claim without an immutable source or an explicitly marked hypothesis origin;
- no observation claim from a synthetic simulation;
- no real-system claim from a synthetic target ID or symbolic action;
- no formal proof admission if checker/theory/proposition scope differs or the checker is unavailable;
- no “verified” boolean without a typed verifier receipt and named verification method;
- preserve counterexamples and contradictory evidence;
- scope every accepted result by asset, version, interface, conditions and observation interval;
- a signature proves signer/integrity within scope, not empirical truth;
- a model's success on training traces is not independent validation.

## 7. Cross-stream ownership

| Stream | Required boundary |
|---|---|
| W01 Identity/Trust | Authenticate requester, owner/controller, observer, verifier and delegation; separate identity from target authority |
| W02 Runtime | Bind observation/test dispatch to operation, authorization and attempt IDs; unknown external outcomes require reconciliation |
| W03 Memory/State | Immutable capture custody, durable evidence store, retention/deletion policy and provenance checkpoints |
| W04 Agent Fabric | Agents may request scope and analyze artifacts; they cannot self-issue owner authorization |
| W05 Routing/Providers | Network tools obey both network egress lease and target-specific observation authorization |
| W06 NEXUS/FRL | Typed claim, source-span, proof and verifier receipts; preserve dissent and scope |
| W07 MIRROR WORLD | Synthetic worlds remain isolated; model-to-reality comparison uses real observation receipts, never synthetic report flags |
| W08 Browser/Device | Browser downloads, logs, local files and device captures receive source custody and consent metadata |
| W09 Security/Audit | Signed, revocable owner authorization; replay protection, capture integrity, incident containment and audit |
| W10 Specialist Intelligence | Qualification for protocol, OS, hardware, industrial and domain-specific interpretation; human escalation |
| W11 Global Operations | Region/data residency, isolated capture workers, key custody and evidence replication/retention |
| W12 Economy/Governance | Permission and evidence do not imply ownership, payment entitlement or authority to publish/disclose findings |

## 8. Required safety and privacy controls

- No credential theft, secret extraction, persistence, stealth, destructive action or lateral movement against real targets.
- No active probing outside the exact owner-authorized scope; no scope expansion through DNS aliases, redirects, shared hosting, cloud tenancy or discovered neighboring assets.
- Treat traces, binaries, protocol payloads and documents as potentially sensitive; minimize collection and redact secrets before model/provider egress.
- Keep source artifacts local/offline by default where practical; any external model or specialist call requires separate data-purpose and network-lease approval.
- Preserve chain of custody and lawful retention; support owner-requested deletion where compatible with legal holds and audit duties.
- Report uncertainty and incomplete coverage. Do not label a suspected weakness as a confirmed vulnerability without reproducible evidence and a defined severity method.
- Responsible disclosure and remediation handoff require owner policy, contact verification and human review.

## 9. New bounded closure gaps

- `GAP-W01-W07-SYSTEM-OWNER-AUTHORIZATION-AND-SCOPE-BINDING`: cyber-range OwnerAuthorization is not a signed, revocable, target/interface/method/time-bound asset-owner delegation; identity and action grants are separate primitives.
- `GAP-W03-W06-OBSERVATION-CAPTURE-CUSTODY-AND-TRANSFORMATION-LINEAGE`: no shared capture manifest proves source, observer, consent, exact bytes/spans, transformations, retention and custody transitions.
- `GAP-W06-SYSTEM-RECONSTRUCTION-CLAIM-AND-COUNTEREXAMPLE-LIFECYCLE`: protocol/system models need claim-scoped observation lineage, competing hypotheses, coverage, counterexamples and revalidation.
- `GAP-W06-INDEPENDENT-RECONSTRUCTION-VERIFIER-AND-HELDOUT-ORACLE`: structural checks and same-pipeline agreement cannot establish independent behavioral equivalence or vulnerability confirmation.
- `GAP-W07-SYNTHETIC-REPORT-FLAG-AND-REALITY-EVIDENCE-SEPARATION`: `SimulationReport.verified=True` is a local symbolic report flag and must never be interpreted as empirical verification or real-target authorization.
- `GAP-W08-W09-CAPTURE-DATA-PRIVACY-AND-EXTERNAL-MODEL-EXPORT`: capture artifacts require sensitivity/consent/retention controls and separate egress authorization before any external model/provider processing.
- `GAP-W10-SYSTEMS-UNDERSTANDING-SPECIALIST-QUALIFICATION`: protocol/OS/hardware/industrial interpretation requires scope-specific qualification, benchmark evidence and escalation.

## 10. Decision and closure status

This is a source-grounded architecture proposal, not an accepted ADR, production penetration-testing feature, reverse-engineering implementation or proof of a real-system weakness. The existing cyber range remains a synthetic symbolic sandbox in the inspected source. No active testing of real targets is authorized by this document.

W01–W12 remain **PARTIAL**. The seven gaps require owner review, architecture decision acceptance, implementation mapping and later isolated adversarial validation.
